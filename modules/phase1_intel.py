import json
from datetime import datetime
from pathlib import Path


def build_scraping_tasks(company_name: str, website: str) -> list[dict]:
    """Return ordered list of scraping tasks for Phase 1."""
    return [
        {"type": "website", "url": website, "purpose": "products_services", "max_pages": 15},
        {"type": "website", "url": f"{website}/blog", "purpose": "content_intelligence", "max_pages": 10},
        {"type": "news", "query": f"{company_name} funding news 2025 2026", "purpose": "trigger_events"},
        {"type": "news", "query": f"{company_name} customer case study results", "purpose": "content_intelligence"},
        {"type": "news", "query": f"{company_name} competitors comparison alternative", "purpose": "competitor_analysis"},
    ]


def prepare_claude_prompt(company_name: str, scraped_data: list[dict]) -> str:
    """Build the analysis prompt for Claude Code to process scraped content."""
    content_blocks = "\n\n".join([
        f"SOURCE: {d.get('url', '')}\nTITLE: {d.get('title', '')}\nCONTENT:\n{d.get('text', '')[:2000]}"
        for d in scraped_data[:12]
    ])
    return f"""You are analyzing {company_name} to build a comprehensive company intelligence profile for a B2B lead generation system.

Based on the scraped content below, extract and structure the intel into this EXACT JSON schema. Be specific — vague answers reduce lead quality.

{{
  "company_profile": {{
    "name": "",
    "website": "",
    "founded": "",
    "headquarters": "",
    "employee_count": "",
    "funding_stage": "",
    "revenue_estimate": "",
    "description": ""
  }},
  "products_services": {{
    "core_product": "",
    "key_features": [],
    "use_cases": [],
    "pricing_model": ""
  }},
  "market_positioning": {{
    "value_proposition": "",
    "market_segment": "",
    "differentiators": [],
    "market_trends": []
  }},
  "ideal_customer_profile": {{
    "target_industries": [],
    "company_size_range": "",
    "agent_count_range": "",
    "revenue_range": "",
    "decision_maker_titles": [],
    "tech_stack_signals": [],
    "pain_points": [],
    "trigger_events": [],
    "qualification_criteria": {{
      "budget_indicators": [],
      "authority_signals": [],
      "timeline_triggers": []
    }}
  }},
  "competitor_analysis": {{
    "direct_competitors": [],
    "indirect_competitors": [],
    "differentiators_vs_competitors": {{}},
    "market_position": ""
  }},
  "warm_lead_signals": {{
    "positive_indicators": [],
    "disqualifiers": []
  }},
  "content_intelligence": {{
    "key_themes": [],
    "case_study_verticals": [],
    "proven_results": []
  }}
}}

SCRAPED CONTENT:
{content_blocks}

Return ONLY the JSON object. No explanation. No markdown fences. Just raw JSON."""


def save_intel(company_name: str, intel: dict, data_dir: str = "data") -> str:
    """Save company intel JSON to disk. Returns absolute file path."""
    company_dir = Path(data_dir) / company_name.lower().replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)
    filepath = company_dir / "company_intel.json"
    intel["_meta"] = {
        "company": company_name,
        "generated_at": datetime.now().isoformat(),
        "generated_by": "Claude Code (interactive)",
    }
    with open(filepath, "w") as f:
        json.dump(intel, f, indent=2)
    return str(filepath)


def load_intel(company_name: str, data_dir: str = "data") -> dict | None:
    """Load existing company intel from disk. Returns None if not found."""
    filepath = Path(data_dir) / company_name.lower().replace(" ", "_") / "company_intel.json"
    if not filepath.exists():
        return None
    with open(filepath) as f:
        return json.load(f)
