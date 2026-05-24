import json
from datetime import datetime
from pathlib import Path

from utils.gemini import generate_with_fallback

_SIGNAL_KEYWORDS = {
    "genesys": "Genesys",
    "nice incontact": "NICE InContact",
    "five9": "Five9",
    "avaya": "Avaya",
    "salesforce": "Salesforce",
    "amazon connect": "Amazon Connect",
    "twilio": "Twilio",
    "observe.ai": "Observe.AI",
    "callminer": "CallMiner",
    "gong": "Gong",
}

_COMPLIANCE_INDUSTRIES = {"financial", "insurance", "healthcare", "banking", "fintech"}


def _filter_tech_signals(tech_str: str) -> list[str]:
    tech_lower = (tech_str or "").lower()
    return [label for kw, label in _SIGNAL_KEYWORDS.items() if kw in tech_lower]


def _map_pain_points(industry: str, all_pain_points: list[str]) -> list[str]:
    industry_lower = (industry or "").lower()
    compliance = [p for p in all_pain_points if "compliance" in p.lower()]
    other = [p for p in all_pain_points if "compliance" not in p.lower()]
    if any(c in industry_lower for c in _COMPLIANCE_INDUSTRIES) and compliance:
        return (compliance + other)[:3]
    return other[:3]


def build_outreach_prompt(lead: dict, intel: dict) -> str:
    positioning = intel.get("market_positioning", {})
    icp = intel.get("ideal_customer_profile", {})
    tech_signals = _filter_tech_signals(lead.get("company_technologies", ""))
    pain_points = _map_pain_points(lead.get("company_industry", ""), icp.get("pain_points", []))
    keywords = [k.strip() for k in (lead.get("company_keywords") or "").split(",") if k.strip()][:5]
    differentiators = positioning.get("differentiators", [])[:3]

    lines = [
        "You are writing sales outreach for Cresta — an enterprise AI platform for contact centers.",
        "",
        "CRESTA:",
        f"  Value prop: {positioning.get('value_proposition', '')}",
        "  Differentiators:",
        *[f"    - {d}" for d in differentiators],
        f"  Relevant pain points for {lead.get('company_industry', 'this industry')}:",
        *[f"    - {p}" for p in pain_points],
        "",
        "PROSPECT:",
        f"  Name: {lead.get('first_name', '')} {lead.get('last_name', '')}, {lead.get('title', '')}",
        f"  Company: {lead.get('company_name', '')} | {lead.get('company_industry', '')} "
        f"| {lead.get('company_employees', '')} employees | ${lead.get('company_revenue', '')} revenue",
    ]
    if tech_signals:
        lines.append(f"  Tech signals: {', '.join(tech_signals)}")
    if keywords:
        lines.append(f"  Business context: {', '.join(k for k in keywords if k)}")

    lines += [
        "",
        "Write three outreach pieces. Be specific — reference their tech stack and industry directly. Be concise and conversational.",
        "",
        "[EMAIL_SUBJECT]",
        "Max 8 words. No spam trigger words.",
        "[EMAIL_BODY]",
        "4-5 sentences: hook on their specific context → pain point → Cresta solution → soft CTA.",
        "[CALL_SCRIPT]",
        "Format: Opener | Discovery Q1 | Discovery Q2 | 30-second pitch",
        "[LINKEDIN]",
        "2-3 sentences: personalized connection request or InMail.",
        "[END]",
    ]
    return "\n".join(lines)


def parse_outreach_response(text: str) -> dict:
    markers = ["[EMAIL_SUBJECT]", "[EMAIL_BODY]", "[CALL_SCRIPT]", "[LINKEDIN]", "[END]"]
    keys = ["email_subject", "email_body", "call_script", "linkedin_message"]
    if not all(m in text for m in markers):
        return {k: "" for k in keys} | {"raw_response": text}
    result = {}
    for i, key in enumerate(keys):
        start = text.index(markers[i]) + len(markers[i])
        end = text.index(markers[i + 1])
        result[key] = text[start:end].strip()
    return result


def generate_outreach(api_keys: list[str], lead: dict, intel: dict) -> dict:
    prompt = build_outreach_prompt(lead, intel)
    try:
        text = generate_with_fallback(api_keys, prompt)
        return parse_outreach_response(text)
    except Exception as e:
        keys = ["email_subject", "email_body", "call_script", "linkedin_message"]
        return {k: "" for k in keys} | {"error": str(e)}


def save_outreach(company_name: str, results: list[dict], data_dir: str = "data") -> str:
    company_dir = Path(data_dir) / company_name.lower().replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)
    filepath = company_dir / "outreach.json"
    output = {
        "_meta": {"company": company_name, "generated_at": datetime.now().isoformat(), "total": len(results)},
        "outreach": results,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return str(filepath)


def load_outreach(company_name: str, data_dir: str = "data") -> list[dict] | None:
    filepath = Path(data_dir) / company_name.lower().replace(" ", "_") / "outreach.json"
    if not filepath.exists():
        return None
    with open(filepath, encoding="utf-8") as f:
        return json.load(f).get("outreach")
