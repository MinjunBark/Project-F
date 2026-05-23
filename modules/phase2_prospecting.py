import json
from datetime import datetime
from pathlib import Path


def build_apollo_queries(intel: dict) -> list[dict]:
    icp = intel.get("ideal_customer_profile", {})
    titles = icp.get("decision_maker_titles", [])[:6]
    return [
        {
            "titles": titles,
            "employee_ranges": ["201,500", "501,1000", "1001,2000", "2001,5000", "5001,10000"],
        }
    ]


def score_lead(person: dict, icp: dict) -> dict:
    scores = {
        "icp_fit": 0,
        "decision_maker": 0,
        "buying_signals": 0,
        "data_completeness": 0,
    }

    # ICP Fit (max 40 points)
    org_industry = (person.get("company_industry") or "").lower()
    target_text = " ".join(icp.get("target_industries", [])).lower()
    industry_keywords = ["financial", "telecom", "airline", "healthcare", "insurance",
                         "retail", "automotive", "travel", "collections"]
    for kw in industry_keywords:
        if kw in org_industry and kw in target_text:
            scores["icp_fit"] += 20
            break

    emp = person.get("company_employees") or 0
    if 100 <= emp <= 10000:
        scores["icp_fit"] += 20
    elif 50 <= emp < 100 or 10000 < emp <= 50000:
        scores["icp_fit"] += 10

    # Decision Maker (max 30 points)
    title = (person.get("title") or "").lower()
    if any(t in title for t in ["chief", "cco", "coo", "cxo", "evp", "svp", "c-suite"]):
        scores["decision_maker"] = 30
    elif any(t in title for t in ["vp", "vice president"]):
        scores["decision_maker"] = 25
    elif "director" in title:
        scores["decision_maker"] = 15
    elif any(t in title for t in ["manager", "head of", "head,", "lead"]):
        scores["decision_maker"] = 8

    # Buying Signals (max 20 points)
    email_status = (person.get("email_status") or "").lower()
    if person.get("email") and email_status in ("verified", "valid"):
        scores["buying_signals"] += 15
    elif person.get("email"):
        scores["buying_signals"] += 8
    if person.get("linkedin_url"):
        scores["buying_signals"] += 5

    # Data Completeness (max 10 points)
    if person.get("email"):
        scores["data_completeness"] += 4
    if person.get("linkedin_url"):
        scores["data_completeness"] += 3
    if person.get("company_employees"):
        scores["data_completeness"] += 2
    if person.get("company_website"):
        scores["data_completeness"] += 1

    total = sum(scores.values())
    stars = (
        5 if total >= 80 else
        4 if total >= 60 else
        3 if total >= 40 else
        2 if total >= 20 else
        1
    )
    return {"scores": scores, "total": total, "stars": stars}


def filter_leads(scored_leads: list[dict], min_stars: int = 3, max_leads: int = 30) -> list[dict]:
    qualified = [l for l in scored_leads if l["scoring"]["stars"] >= min_stars]
    qualified.sort(key=lambda l: l["scoring"]["total"], reverse=True)
    return qualified[:max_leads]


def save_leads(company_name: str, leads: list[dict], data_dir: str = "data") -> str:
    company_dir = Path(data_dir) / company_name.lower().replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)
    filepath = company_dir / "raw_leads.json"
    output = {
        "_meta": {
            "company": company_name,
            "generated_at": datetime.now().isoformat(),
            "total_leads": len(leads),
        },
        "leads": leads,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return str(filepath)


def load_leads(company_name: str, data_dir: str = "data") -> list[dict] | None:
    filepath = Path(data_dir) / company_name.lower().replace(" ", "_") / "raw_leads.json"
    if not filepath.exists():
        return None
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("leads")


def _seen_path(company_name: str, data_dir: str = "data") -> Path:
    return Path(data_dir) / company_name.lower().replace(" ", "_") / "seen_leads.json"


def load_seen(company_name: str, data_dir: str = "data") -> set:
    path = _seen_path(company_name, data_dir)
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("seen", []))


def filter_seen(leads: list[dict], seen: set) -> list[dict]:
    fresh = []
    for lead in leads:
        key = lead.get("email") or lead.get("linkedin_url")
        if key is None or key not in seen:
            fresh.append(lead)
    return fresh


def save_seen(company_name: str, leads: list[dict], existing_seen: set, data_dir: str = "data"):
    path = _seen_path(company_name, data_dir)
    updated = set(existing_seen)
    for lead in leads:
        if lead.get("email"):
            updated.add(lead["email"])
        if lead.get("linkedin_url"):
            updated.add(lead["linkedin_url"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seen": sorted(updated)}, indent=2), encoding="utf-8")
