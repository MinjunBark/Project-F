import argparse
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import config
from modules.phase1_intel import load_intel
from modules.phase2_prospecting import (
    _stars,
    filter_leads,
    filter_seen,
    load_seen,
    save_leads,
    save_seen,
    score_lead,
)
from utils.discord import phase_complete
from utils.hunter import verify_email
from utils.sheets import get_client as get_sheets_client, write_leads

COMPETITORS = {
    "liveperson", "8x8", "avaya", "ringcentral", "dialpad", "nextiva",
    "sinch", "uniphore", "bandwidth.com", "sprinklr", "medallia", "genesys",
    "nice systems", "five9", "twilio", "observe.ai", "balto", "gong",
    "callminer", "liveops",
}


CRESTA_TECH_SIGNALS = [
    "genesys", "nice", "five9", "amazon connect", "twilio",
    "salesforce service", "avaya", "observe.ai", "callminer", "gong",
]


def _normalize(item: dict) -> dict:
    founded = item.get("company_founded_year")
    return {
        "first_name": item.get("first_name", ""),
        "last_name": item.get("last_name", ""),
        "name": item.get("full_name", ""),
        "title": item.get("job_title", ""),
        "email": item.get("email", ""),
        "email_status": "unverified",
        "personal_phone": item.get("mobile_number") or "",
        "linkedin_url": item.get("linkedin", ""),
        "company_name": item.get("company_name", ""),
        "company_website": item.get("company_website", ""),
        "company_industry": item.get("industry", ""),
        "company_employees": item.get("company_size") or 0,
        "company_technologies": item.get("company_technologies", ""),
        "company_keywords": item.get("keywords", ""),
        "company_revenue": item.get("company_annual_revenue_clean", ""),
        "company_phone": item.get("company_phone", ""),
        "company_total_funding_clean": item.get("company_total_funding_clean") or "",
        "company_age": str(2026 - int(founded)) if founded and str(founded).isdigit() else "",
        "source": "import",
    }


def _is_competitor(person: dict) -> bool:
    name = (person.get("company_name") or "").lower()
    if any(c in name for c in COMPETITORS):
        return True
    tech = (person.get("company_technologies") or "").lower()
    if "liveperson monitor" in tech or "8x8" in tech:
        return True
    return False


def _seniority_key(p: dict) -> int:
    title = (p.get("title") or "").lower()
    if any(t in title for t in ["chief", "cco", "coo", "cxo", "evp", "svp"]):
        return 0
    if any(t in title for t in ["vp", "vice president"]):
        return 1
    if "director" in title:
        return 2
    if any(t in title for t in ["manager", "head"]):
        return 3
    return 4


def _company_dedup(people: list[dict], max_per_company: int = 2) -> list[dict]:
    grouped = defaultdict(list)
    for p in people:
        grouped[p["company_name"].lower()].append(p)
    result = []
    for contacts in grouped.values():
        contacts.sort(key=_seniority_key)
        result.extend(contacts[:max_per_company])
    return result


def _apply_tech_bonus(scoring: dict, person: dict) -> dict:
    tech = (person.get("company_technologies") or "").lower()
    if any(sig in tech for sig in CRESTA_TECH_SIGNALS):
        scoring["scores"]["buying_signals"] += 10
        scoring["total"] = sum(scoring["scores"].values())
        scoring["stars"] = _stars(scoring["total"])
    return scoring


def main():
    parser = argparse.ArgumentParser(description="Import code_crafter leads export into Project F pipeline")
    parser.add_argument("--company", required=True, help="Company name (must match Company List sheet)")
    parser.add_argument("--file", required=True, help="Path to JSON export from Apify")
    parser.add_argument("--no-email-verify", action="store_true", help="Skip Hunter.io email verification")
    parser.add_argument("--no-sheets", action="store_true", help="Skip writing to Google Sheets")
    args = parser.parse_args()

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        raw = json.load(f)

    items = raw if isinstance(raw, list) else raw.get("items") or raw.get("leads") or []
    print(f"Loaded {len(items)} items from {filepath.name}")

    intel = load_intel(args.company)
    if not intel:
        print(f"ERROR: No intel found for '{args.company}'. Run Phase 1 first.")
        sys.exit(1)

    icp = intel.get("ideal_customer_profile", {})

    # Normalize
    people = [_normalize(item) for item in items if not item.get("error")]

    # Filter competitors
    before = len(people)
    people = [p for p in people if not _is_competitor(p)]
    print(f"Filtered {before - len(people)} competitors - {len(people)} remaining")

    # Company dedup
    before = len(people)
    people = _company_dedup(people)
    print(f"Company dedup: {before} -> {len(people)} contacts (capped at 2 per company)")

    # Seen dedup
    seen = load_seen(args.company)
    people = filter_seen(people, seen)
    print(f"After seen dedup: {len(people)} candidates")

    if not people:
        print("No new candidates after dedup. Exiting.")
        sys.exit(0)

    # Score
    scored = []
    for person in people:
        scoring = score_lead(person, icp)
        scoring = _apply_tech_bonus(scoring, person)
        scored.append({**person, "scoring": scoring})

    leads = filter_leads(
        scored,
        min_stars=config.MIN_STAR_RATING_FOR_OUTREACH,
        max_leads=config.MAX_LEADS_PER_RUN,
    )
    print(f"Qualified leads ({config.MIN_STAR_RATING_FOR_OUTREACH}+ stars): {len(leads)}")

    if not leads:
        print("No leads passed the scoring threshold. Try lowering MIN_STAR_RATING_FOR_OUTREACH in .env.")
        sys.exit(0)

    print("\nTop leads:")
    for lead in leads[:10]:
        s = lead["scoring"]
        rev = lead.get("company_revenue", "")
        emp = lead.get("company_employees", "")
        print(
            f"  [{s['stars']}* {s['total']:3}pts] {lead.get('name','?'):25} "
            f"- {lead.get('title','?')[:40]:40} "
            f"@ {lead.get('company_name','?')[:28]:28} "
            f"| {lead.get('company_industry','')[:20]:20} "
            f"| {emp:>6} emp | {rev}"
        )

    # Email verification
    if not args.no_email_verify:
        print("\nVerifying emails with Hunter.io...")
        for lead in leads:
            if lead.get("email"):
                try:
                    result = verify_email(config.HUNTER_API_KEY, lead["email"])
                    lead["email_status"] = result["status"]
                    lead["hunter_score"] = result["score"]
                except Exception as e:
                    print(f"  WARNING: Hunter verify failed for {lead.get('email', '')}: {e}")

    # Save
    filepath_out = save_leads(args.company, leads)
    save_seen(args.company, leads, seen)
    print(f"\nSaved {len(leads)} leads → {filepath_out}")

    if not args.no_sheets:
        print("Writing to Google Sheets...")
        sheets = get_sheets_client(config.GOOGLE_CREDENTIALS_PATH)
        write_leads(sheets, config.SPREADSHEET_ID, args.company, leads)
        print("Google Sheets updated.")

    if config.DISCORD_WEBHOOK_LEADS:
        phase_complete(
            config.DISCORD_WEBHOOK_LEADS,
            "phase2",
            args.company,
            f"{len(leads)} leads imported, scored, and saved. Leads sheet updated.",
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
