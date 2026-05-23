import pytest
import json
from pathlib import Path

SAMPLE_ICP = {
    "target_industries": [
        "Financial Services", "Airlines and Travel", "Telecommunications", "Healthcare"
    ],
    "decision_maker_titles": [
        "VP of Customer Experience",
        "VP of Contact Center Operations",
        "Chief Customer Officer",
        "Director of Quality Management",
    ],
    "company_size_range": "1,000-50,000 employees",
    "agent_count_range": "100-10,000+ contact center agents",
}

SAMPLE_INTEL = {"ideal_customer_profile": SAMPLE_ICP}


def _make_person(**overrides):
    base = {
        "first_name": "Jane",
        "last_name": "Doe",
        "name": "Jane Doe",
        "title": "VP of Customer Experience",
        "email": "jane@acme.com",
        "email_status": "verified",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "company_industry": "Telecommunications",
        "company_employees": 5000,
        "apollo_id": "abc123",
    }
    base.update(overrides)
    return base


# --- build_apollo_queries ---

def test_build_apollo_queries_returns_list():
    from modules.phase2_prospecting import build_apollo_queries
    queries = build_apollo_queries(SAMPLE_INTEL)
    assert isinstance(queries, list)
    assert len(queries) >= 1


def test_build_apollo_queries_includes_titles():
    from modules.phase2_prospecting import build_apollo_queries
    queries = build_apollo_queries(SAMPLE_INTEL)
    assert len(queries[0]["titles"]) >= 1
    assert any("VP" in t or "Director" in t or "Chief" in t for t in queries[0]["titles"])


def test_build_apollo_queries_includes_employee_ranges():
    from modules.phase2_prospecting import build_apollo_queries
    queries = build_apollo_queries(SAMPLE_INTEL)
    assert len(queries[0]["employee_ranges"]) >= 1


# --- score_lead ---

def test_score_lead_vp_title_gets_high_decision_maker_score():
    from modules.phase2_prospecting import score_lead
    person = _make_person(title="VP of Customer Experience")
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["decision_maker"] >= 25


def test_score_lead_director_title_gets_partial_decision_maker_score():
    from modules.phase2_prospecting import score_lead
    person = _make_person(title="Director of Operations")
    result = score_lead(person, SAMPLE_ICP)
    assert 10 <= result["scores"]["decision_maker"] < 25


def test_score_lead_manager_title_gets_low_decision_maker_score():
    from modules.phase2_prospecting import score_lead
    person = _make_person(title="Customer Service Manager")
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["decision_maker"] < 15


def test_score_lead_matching_industry_gets_icp_points():
    from modules.phase2_prospecting import score_lead
    person = _make_person(company_industry="Telecommunications")
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["icp_fit"] >= 15


def test_score_lead_matching_employee_count_gets_icp_points():
    from modules.phase2_prospecting import score_lead
    person = _make_person(company_employees=5000)
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["icp_fit"] >= 15


def test_score_lead_with_verified_email_gets_buying_signal_points():
    from modules.phase2_prospecting import score_lead
    person = _make_person(email="jane@acme.com", email_status="verified")
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["buying_signals"] >= 10


def test_score_lead_no_email_gets_zero_buying_signal_from_email():
    from modules.phase2_prospecting import score_lead
    person = _make_person(email="", email_status="")
    result = score_lead(person, SAMPLE_ICP)
    assert result["scores"]["buying_signals"] < 15


def test_score_lead_high_score_returns_5_stars():
    from modules.phase2_prospecting import score_lead
    person = _make_person(
        title="Chief Customer Officer",
        company_industry="Telecommunications",
        company_employees=5000,
        email="jane@acme.com",
        email_status="verified",
        linkedin_url="https://linkedin.com/in/janedoe",
        company_website="https://acme.com",
    )
    result = score_lead(person, SAMPLE_ICP)
    assert result["stars"] >= 4


def test_score_lead_low_score_returns_low_stars():
    from modules.phase2_prospecting import score_lead
    person = _make_person(
        title="Customer Service Rep",
        company_industry="Unknown",
        company_employees=10,
        email="",
        email_status="",
        linkedin_url="",
        company_website="",
    )
    result = score_lead(person, SAMPLE_ICP)
    assert result["stars"] <= 2


def test_score_lead_returns_required_keys():
    from modules.phase2_prospecting import score_lead
    result = score_lead(_make_person(), SAMPLE_ICP)
    assert "scores" in result
    assert "total" in result
    assert "stars" in result
    assert set(result["scores"].keys()) == {"icp_fit", "decision_maker", "buying_signals", "data_completeness"}


# --- filter_leads ---

def test_filter_leads_removes_below_min_stars():
    from modules.phase2_prospecting import filter_leads
    leads = [
        {**_make_person(), "scoring": {"stars": 2, "total": 30, "scores": {}}},
        {**_make_person(), "scoring": {"stars": 4, "total": 70, "scores": {}}},
    ]
    result = filter_leads(leads, min_stars=3)
    assert len(result) == 1
    assert result[0]["scoring"]["stars"] == 4


def test_filter_leads_respects_max_leads():
    from modules.phase2_prospecting import filter_leads
    leads = [
        {**_make_person(), "scoring": {"stars": 4, "total": 60 + i, "scores": {}}}
        for i in range(10)
    ]
    result = filter_leads(leads, min_stars=3, max_leads=5)
    assert len(result) == 5


def test_filter_leads_sorts_by_total_score_descending():
    from modules.phase2_prospecting import filter_leads
    leads = [
        {**_make_person(), "scoring": {"stars": 3, "total": 45, "scores": {}}},
        {**_make_person(), "scoring": {"stars": 5, "total": 90, "scores": {}}},
        {**_make_person(), "scoring": {"stars": 4, "total": 70, "scores": {}}},
    ]
    result = filter_leads(leads, min_stars=3)
    assert result[0]["scoring"]["total"] == 90
    assert result[1]["scoring"]["total"] == 70


# --- save_leads / load_leads ---

def test_save_leads_creates_json_file(tmp_path):
    from modules.phase2_prospecting import save_leads
    leads = [_make_person()]
    filepath = save_leads("Cresta", leads, data_dir=str(tmp_path))
    assert Path(filepath).exists()


def test_save_leads_includes_meta(tmp_path):
    from modules.phase2_prospecting import save_leads
    leads = [_make_person()]
    filepath = save_leads("Cresta", leads, data_dir=str(tmp_path))
    with open(filepath, encoding="utf-8") as f:
        saved = json.load(f)
    assert "_meta" in saved
    assert saved["_meta"]["company"] == "Cresta"
    assert saved["_meta"]["total_leads"] == 1


def test_load_leads_returns_none_if_missing(tmp_path):
    from modules.phase2_prospecting import load_leads
    assert load_leads("NoCompany", data_dir=str(tmp_path)) is None


def test_load_leads_round_trips_data(tmp_path):
    from modules.phase2_prospecting import save_leads, load_leads
    leads = [_make_person()]
    save_leads("Cresta", leads, data_dir=str(tmp_path))
    loaded = load_leads("Cresta", data_dir=str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Jane Doe"
