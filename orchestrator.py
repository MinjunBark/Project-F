import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import config
from modules.phase1_intel import build_scraping_tasks, prepare_claude_prompt, save_intel, load_intel
from modules.phase2_prospecting import build_apollo_queries, score_lead, filter_leads, save_leads, load_leads, load_seen, filter_seen, save_seen
from utils.gemini import get_client as get_gemini_client
from modules.phase3_outreach import generate_outreach, save_outreach, load_outreach
from utils.leads_finder import search_leads, extract_people as extract_leads_finder_people
from utils.apify import get_client as get_apify_client, scrape_website, search_google
from utils.discord import phase_complete, phase_error
from utils.hunter import verify_email, find_email
from utils.sheets import (
    get_client as get_sheets_client,
    get_company,
    update_company_last_run,
    write_company_intel,
    write_leads,
    write_outreach,
)


def _state_path(company_name: str) -> Path:
    return Path("data") / company_name.lower().replace(" ", "_") / "state.json"


def load_state(company_name: str) -> dict:
    path = _state_path(company_name)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"company": company_name, "completed_phases": [], "started_at": datetime.now().isoformat()}


def save_state(company_name: str, state: dict):
    path = _state_path(company_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def run_phase1(company: dict, state: dict, resume: bool) -> dict | None:
    """
    Scrapes the client company and saves a prompt for Claude Code analysis.
    Returns intel dict if already complete (resume), or None if human action required.
    """
    company_name = company["Company Name"]

    if resume and "phase1" in state["completed_phases"]:
        existing = load_intel(company_name)
        if existing:
            print("  [SKIP] Phase 1 already complete. Loading existing intel.")
            return existing

    # If intel file already exists from a previous partial run, load it
    existing = load_intel(company_name)
    if existing and resume:
        print("  [FOUND] Intel file exists — will write to Sheets if not already complete.")
        return existing

    print("\n" + "=" * 60)
    print("PHASE 1: COMPANY INTELLIGENCE")
    print("=" * 60)

    apify = get_apify_client(config.APIFY_TOKEN)
    tasks = build_scraping_tasks(company_name, company["Website"])
    scraped_data = []

    for task in tasks:
        label = task.get("url", task.get("query", ""))
        print(f"  Scraping: {label[:80]}...")
        try:
            if task["type"] == "website":
                pages = scrape_website(apify, task["url"], max_pages=task.get("max_pages", 10))
                scraped_data.extend(pages)
                print(f"    -> {len(pages)} pages collected")
            elif task["type"] == "news":
                results = search_google(apify, task["query"])
                scraped_data.extend(results)
                print(f"    -> {len(results)} results collected")
        except Exception as e:
            print(f"  WARNING: scrape failed for {label[:60]}: {e}")

    # Save raw data and prompt
    company_dir = Path("data") / company_name.lower().replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)

    raw_path = company_dir / "phase1_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2, ensure_ascii=False)

    prompt = prepare_claude_prompt(company_name, scraped_data)
    prompt_path = company_dir / "phase1_prompt.txt"
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"\n  Raw data saved:  {raw_path}  ({len(scraped_data)} items)")
    print(f"  Prompt saved:    {prompt_path}")
    print("\n" + "=" * 60)
    print("ACTION REQUIRED — Claude Code Analysis")
    print("=" * 60)
    print(f"1. Open:  {prompt_path}")
    print("2. Paste the full contents to Claude Code in your conversation")
    print("3. Save the JSON response Claude Code returns to:")
    print(f"   data/{company_name.lower().replace(' ', '_')}/company_intel.json")
    print(f"4. Re-run: python orchestrator.py --company \"{company_name}\" --resume")
    print("=" * 60)

    return None  # Signals human action required


def run_phase2(company: dict, state: dict, resume: bool) -> list[dict] | None:
    """
    Searches for ICP-matched leads via Apify leads-finder, scores them, verifies emails with Hunter,
    and saves results. Returns lead list if complete, None if phase is blocked.
    """
    company_name = company["Company Name"]

    if resume and "phase2" in state["completed_phases"]:
        existing = load_leads(company_name)
        if existing:
            print("  [SKIP] Phase 2 already complete. Loading existing leads.")
            return existing

    intel = load_intel(company_name)
    if not intel:
        print("  ERROR: No intel found for phase 2. Run Phase 1 first.")
        return None

    print("\n" + "=" * 60)
    print("PHASE 2: PROSPECTING")
    print("=" * 60)

    icp = intel.get("ideal_customer_profile", {})
    queries = build_apollo_queries(intel)
    seen = load_seen(company_name)
    apify = get_apify_client(config.APIFY_TOKEN)
    all_people = []

    for query in queries:
        label = ", ".join(query["titles"][:2])
        print(f"  Searching Leads Finder: {label[:70]}...")
        try:
            items = search_leads(
                apify,
                job_titles=query["titles"],
                company_sizes=["201 - 500", "501 - 1000", "1001 - 5000", "5001 - 10000"],
                limit=config.MAX_LEADS_PER_RUN * 3,
            )
            people = extract_leads_finder_people(items)
            all_people.extend(people)
            print(f"    -> {len(people)} candidates found")
        except RuntimeError:
            raise
        except Exception as e:
            print(f"  WARNING: Leads Finder search failed: {e}")

    all_people = filter_seen(all_people, seen)
    print(f"  Total candidates (after dedup): {len(all_people)}")

    scored = []
    for person in all_people:
        scoring = score_lead(person, icp)
        scored.append({**person, "scoring": scoring})

    leads = filter_leads(
        scored,
        min_stars=config.MIN_STAR_RATING_FOR_OUTREACH,
        max_leads=config.MAX_LEADS_PER_RUN,
    )
    print(f"  Qualified leads ({config.MIN_STAR_RATING_FOR_OUTREACH}+ stars): {len(leads)}")

    print("  Verifying emails with Hunter.io...")
    for lead in leads:
        if lead.get("email"):
            try:
                result = verify_email(config.HUNTER_API_KEY, lead["email"])
                lead["email_status"] = result["status"]
                lead["hunter_score"] = result["score"]
            except Exception as e:
                print(f"  WARNING: Hunter verify failed for {lead.get('email', '')}: {e}")
        elif lead.get("company_website"):
            domain = urlparse(lead["company_website"]).netloc
            try:
                result = find_email(
                    config.HUNTER_API_KEY, domain, lead["first_name"], lead["last_name"]
                )
                if result["email"]:
                    lead["email"] = result["email"]
                    lead["email_status"] = "found"
                    lead["hunter_score"] = result["confidence"]
            except Exception as e:
                print(f"  WARNING: Hunter find failed for {lead.get('name', '')}: {e}")

    filepath = save_leads(company_name, leads)
    save_seen(company_name, leads, seen)
    print(f"  Leads saved: {filepath} ({len(leads)} leads)")

    return leads


def run_phase3(company: dict, state: dict, resume: bool) -> list[dict] | None:
    company_name = company["Company Name"]

    if resume and "phase3" in state["completed_phases"]:
        existing = load_outreach(company_name)
        if existing:
            print("  [SKIP] Phase 3 already complete. Loading existing outreach.")
            return existing

    leads = load_leads(company_name)
    if not leads:
        print("  ERROR: No leads found for phase 3. Run Phase 2 first.")
        return None

    intel = load_intel(company_name)
    if not intel:
        print("  ERROR: No intel found for phase 3. Run Phase 1 first.")
        return None

    print("\n" + "=" * 60)
    print("PHASE 3: OUTREACH GENERATION")
    print("=" * 60)

    gemini = get_gemini_client(config.GEMINI_API_KEY)
    results = []

    for i, lead in enumerate(leads):
        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
        print(f"  [{i+1}/{len(leads)}] {name} @ {lead.get('company_name', '')}...")
        outreach = generate_outreach(gemini, lead, intel)
        results.append({**lead, **outreach})
        if i < len(leads) - 1:
            time.sleep(4)

    filepath = save_outreach(company_name, results)
    print(f"  Outreach saved: {filepath} ({len(results)} entries)")

    return results


def main():
    parser = argparse.ArgumentParser(description="Project F Lead Generation Orchestrator")
    parser.add_argument("--company", required=True, help="Company name (must match Company List sheet)")
    parser.add_argument("--resume", action="store_true", help="Skip completed phases and resume from state")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific phase only")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"PROJECT F — {args.company.upper()}")
    print(f"{'=' * 60}")

    # Validate company exists in Google Sheet
    sheets = get_sheets_client(config.GOOGLE_CREDENTIALS_PATH)
    company = get_company(sheets, config.SPREADSHEET_ID, args.company)

    if not company:
        print(f"\nERROR: '{args.company}' not found in Company List sheet.")
        print("Check the company name matches exactly (case-insensitive).")
        sys.exit(1)

    if company.get("Status", "Active") != "Active":
        print(f"\nERROR: '{args.company}' is currently Paused.")
        print("Update Status to 'Active' in the Company List sheet to run.")
        sys.exit(1)

    print(f"Company: {company['Company Name']} ({company['Website']})")
    state = load_state(args.company)

    if state["completed_phases"]:
        print(f"Completed phases: {state['completed_phases']}")

    # --- Phase 1 ---
    if not args.phase or args.phase == 1:
        intel = run_phase1(company, state, args.resume)

        if intel is None:
            print("\nRun paused — waiting for Claude Code analysis.")
            print("Follow the instructions above, then re-run with --resume.")
            return

        if "phase1" not in state["completed_phases"]:
            print("\n  Writing intel to Google Sheets...")
            write_company_intel(sheets, config.SPREADSHEET_ID, company["Company Name"], intel)
            state["completed_phases"].append("phase1")
            save_state(args.company, state)

            if config.DISCORD_WEBHOOK_UPDATES:
                phase_complete(
                    config.DISCORD_WEBHOOK_UPDATES,
                    "phase1",
                    company["Company Name"],
                    f"Company intel built — ICP extracted. Sheet 2 updated."
                )
            print("  [OK] Phase 1 complete. Intel written to Google Sheets.")

    # --- Phase 2 ---
    if not args.phase or args.phase == 2:
        if args.phase == 2 or "phase1" in state["completed_phases"]:
            leads = run_phase2(company, state, args.resume)

            if leads is None:
                print("\nRun paused — Phase 2 could not complete.")
                return

            if "phase2" not in state["completed_phases"]:
                print("\n  Writing leads to Google Sheets...")
                write_leads(sheets, config.SPREADSHEET_ID, company["Company Name"], leads)
                state["completed_phases"].append("phase2")
                save_state(args.company, state)

                if config.DISCORD_WEBHOOK_LEADS:
                    phase_complete(
                        config.DISCORD_WEBHOOK_LEADS,
                        "phase2",
                        company["Company Name"],
                        f"{len(leads)} leads scored and saved. Leads sheet updated.",
                    )
                print(f"  [OK] Phase 2 complete. {len(leads)} leads written to Google Sheets.")

    # --- Phase 3 ---
    if not args.phase or args.phase == 3:
        if args.phase == 3 or "phase2" in state["completed_phases"]:
            outreach = run_phase3(company, state, args.resume)

            if outreach is None:
                print("\nRun paused — Phase 3 could not complete.")
                return

            if "phase3" not in state["completed_phases"]:
                print("\n  Writing outreach to Google Sheets...")
                write_outreach(sheets, config.SPREADSHEET_ID, company["Company Name"], outreach)
                state["completed_phases"].append("phase3")
                save_state(args.company, state)

                if config.DISCORD_WEBHOOK_UPDATES:
                    phase_complete(
                        config.DISCORD_WEBHOOK_UPDATES,
                        "phase3",
                        company["Company Name"],
                        f"{len(outreach)} outreach templates generated. Outreach sheet updated.",
                    )
                print(f"  [OK] Phase 3 complete. {len(outreach)} outreach templates written to Google Sheets.")

    # Update last run tracking
    update_company_last_run(sheets, config.SPREADSHEET_ID, args.company)
    print(f"\nRun complete. Completed phases: {state['completed_phases']}")


if __name__ == "__main__":
    main()
