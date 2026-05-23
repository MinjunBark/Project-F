# Phase 2 — Prospecting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use Apollo.io to find 15–30 ICP-matched prospects for a selected company, score each lead with a weighted rubric, verify emails with Hunter.io, save to disk, and write to Google Sheets.

**Architecture:** Apollo People Search API finds raw candidates filtered by decision-maker title and company size. A pure-Python scoring engine (no external calls) ranks candidates by ICP Fit 40% / Decision Maker 30% / Buying Signals 20% / Data Completeness 10%, converting the total to 1–5 stars. Only 3+ star leads proceed. Hunter.io verifies or finds emails for qualified leads. Results write to a new per-company tab in Google Sheets and a local `raw_leads.json`. Orchestrator state tracks completion so `--resume` skips this phase.

**Tech Stack:** Python 3.11+, requests, gspread, Apollo.io REST API v1, Hunter.io REST API v2, pytest, pytest-mock

---

## Pre-requisites

Confirm the following before starting any task:
- `data/cresta/company_intel.json` exists (Phase 1 complete)
- `.env` has `APOLLO_API_KEY` and `HUNTER_API_KEY` filled in (no leading spaces)
- `config.py` already exposes `APOLLO_API_KEY`, `HUNTER_API_KEY`, `MAX_LEADS_PER_RUN`, `MIN_STAR_RATING_FOR_OUTREACH`

---

## File Map

```
utils/
  apollo.py              ← Apollo REST API wrapper: search_people, extract_people
  hunter.py              ← Hunter.io wrapper: verify_email, find_email
  sheets.py              ← ADD write_leads() to existing file
modules/
  phase2_prospecting.py  ← build_apollo_queries, score_lead, filter_leads, save_leads, load_leads
tests/
  test_apollo.py         ← unit tests (mocked requests.post)
  test_hunter.py         ← unit tests (mocked requests.get)
  test_phase2.py         ← unit tests for prospecting logic (no I/O)
  test_sheets.py         ← ADD write_leads tests to existing file
orchestrator.py          ← ADD run_phase2(), integrate into main()
data/cresta/
  raw_leads.json         ← auto-created by phase2
```

---

## Task 1: Apollo API Utility

**Files:**
- Create: `utils/apollo.py`
- Create: `tests/test_apollo.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_apollo.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def _mock_post(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


SAMPLE_APOLLO_RESPONSE = {
    "people": [
        {
            "id": "abc123",
            "first_name": "Jane",
            "last_name": "Doe",
            "name": "Jane Doe",
            "title": "VP of Customer Experience",
            "email": "jane.doe@acme.com",
            "email_status": "verified",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "organization": {
                "name": "Acme Corp",
                "website_url": "https://acme.com",
                "industry": "Telecommunications",
                "estimated_num_employees": 5000,
            },
        }
    ],
    "pagination": {"total_entries": 1, "per_page": 25, "page": 1},
}


def test_search_people_posts_to_correct_url():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)) as mock_post:
        from utils.apollo import search_people
        search_people("fake_key", titles=["VP of CX"], employee_ranges=["100,1000"])
        assert "apollo.io" in mock_post.call_args[0][0]


def test_search_people_includes_api_key_in_body():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)) as mock_post:
        from utils.apollo import search_people
        search_people("my_key", titles=["VP of CX"], employee_ranges=["100,1000"])
        body = mock_post.call_args[1]["json"]
        assert body["api_key"] == "my_key"


def test_search_people_returns_response_dict():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)):
        from utils.apollo import search_people
        result = search_people("key", titles=["VP of CX"], employee_ranges=["100,1000"])
        assert "people" in result


def test_extract_people_returns_normalized_list():
    from utils.apollo import extract_people
    people = extract_people(SAMPLE_APOLLO_RESPONSE)
    assert len(people) == 1
    p = people[0]
    assert p["first_name"] == "Jane"
    assert p["title"] == "VP of Customer Experience"
    assert p["company_name"] == "Acme Corp"
    assert p["company_employees"] == 5000


def test_extract_people_handles_missing_organization():
    from utils.apollo import extract_people
    response = {"people": [{"id": "x", "first_name": "Bob", "last_name": "Smith",
                             "name": "Bob Smith", "title": "Director", "email": "",
                             "email_status": "", "linkedin_url": ""}]}
    people = extract_people(response)
    assert len(people) == 1
    assert people[0]["company_name"] == ""
    assert people[0]["company_employees"] is None


def test_extract_people_returns_empty_for_empty_response():
    from utils.apollo import extract_people
    people = extract_people({"people": []})
    assert people == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_apollo.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.apollo'`

- [ ] **Step 3: Create `utils/apollo.py`**

```python
import requests

APOLLO_BASE_URL = "https://api.apollo.io/v1"


def search_people(
    api_key: str,
    titles: list[str],
    employee_ranges: list[str],
    per_page: int = 25,
    page: int = 1,
) -> dict:
    """Search Apollo for people matching title and company size criteria."""
    response = requests.post(
        f"{APOLLO_BASE_URL}/mixed_people/search",
        json={
            "api_key": api_key,
            "page": page,
            "per_page": per_page,
            "person_titles": titles,
            "organization_num_employees_ranges": employee_ranges,
        },
        headers={"Content-Type": "application/json", "Cache-Control": "no-cache"},
    )
    response.raise_for_status()
    return response.json()


def extract_people(response: dict) -> list[dict]:
    """Normalize Apollo API response into a flat list of person dicts."""
    people = []
    for p in response.get("people", []):
        org = p.get("organization") or {}
        people.append({
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "name": p.get("name", ""),
            "title": p.get("title", ""),
            "email": p.get("email", ""),
            "email_status": p.get("email_status", ""),
            "linkedin_url": p.get("linkedin_url", ""),
            "company_name": org.get("name", ""),
            "company_website": org.get("website_url", ""),
            "company_industry": org.get("industry", ""),
            "company_employees": org.get("estimated_num_employees"),
            "apollo_id": p.get("id", ""),
        })
    return people
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_apollo.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add utils/apollo.py tests/test_apollo.py
git commit -m "feat: add Apollo API utility for people search"
```

---

## Task 2: Hunter.io API Utility

**Files:**
- Create: `utils/hunter.py`
- Create: `tests/test_hunter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_hunter.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def _mock_get(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


VERIFY_RESPONSE = {
    "data": {
        "status": "valid",
        "score": 92,
        "email": "jane.doe@acme.com",
    }
}

FIND_RESPONSE = {
    "data": {
        "email": "j.doe@acme.com",
        "confidence": 78,
    }
}

FIND_EMPTY_RESPONSE = {"data": {"email": None, "confidence": 0}}


def test_verify_email_returns_status_and_score():
    with patch("utils.hunter.requests.get", return_value=_mock_get(VERIFY_RESPONSE)):
        from utils.hunter import verify_email
        result = verify_email("fake_key", "jane.doe@acme.com")
        assert result["status"] == "valid"
        assert result["score"] == 92
        assert result["email"] == "jane.doe@acme.com"


def test_verify_email_raises_on_http_error():
    mock = _mock_get({}, status_code=401)
    mock.raise_for_status.side_effect = Exception("401 Unauthorized")
    with patch("utils.hunter.requests.get", return_value=mock):
        from utils.hunter import verify_email
        with pytest.raises(Exception):
            verify_email("bad_key", "x@y.com")


def test_find_email_returns_email_and_confidence():
    with patch("utils.hunter.requests.get", return_value=_mock_get(FIND_RESPONSE)):
        from utils.hunter import find_email
        result = find_email("fake_key", "acme.com", "Jane", "Doe")
        assert result["email"] == "j.doe@acme.com"
        assert result["confidence"] == 78


def test_find_email_returns_empty_string_if_not_found():
    with patch("utils.hunter.requests.get", return_value=_mock_get(FIND_EMPTY_RESPONSE)):
        from utils.hunter import find_email
        result = find_email("fake_key", "acme.com", "Unknown", "Person")
        assert result["email"] == ""
        assert result["confidence"] == 0


def test_verify_email_passes_api_key_in_params():
    with patch("utils.hunter.requests.get", return_value=_mock_get(VERIFY_RESPONSE)) as mock_get:
        from utils.hunter import verify_email
        verify_email("mykey", "test@test.com")
        params = mock_get.call_args[1]["params"]
        assert params["api_key"] == "mykey"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_hunter.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.hunter'`

- [ ] **Step 3: Create `utils/hunter.py`**

```python
import requests

HUNTER_BASE_URL = "https://api.hunter.io/v2"


def verify_email(api_key: str, email: str) -> dict:
    """Verify an email address. Returns dict with email, status, and score."""
    response = requests.get(
        f"{HUNTER_BASE_URL}/email-verifier",
        params={"email": email, "api_key": api_key},
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    return {
        "email": email,
        "status": data.get("status", "unknown"),
        "score": data.get("score", 0),
    }


def find_email(api_key: str, domain: str, first_name: str, last_name: str) -> dict:
    """Find the email for a person at a domain. Returns dict with email and confidence."""
    response = requests.get(
        f"{HUNTER_BASE_URL}/email-finder",
        params={
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": api_key,
        },
    )
    response.raise_for_status()
    data = response.json().get("data", {})
    return {
        "email": data.get("email") or "",
        "confidence": data.get("confidence", 0),
    }
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_hunter.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add utils/hunter.py tests/test_hunter.py
git commit -m "feat: add Hunter.io email verification and finder utility"
```

---

## Task 3: Phase 2 Prospecting Module

**Files:**
- Create: `modules/phase2_prospecting.py`
- Create: `tests/test_phase2.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_phase2.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_phase2.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.phase2_prospecting'`

- [ ] **Step 3: Create `modules/phase2_prospecting.py`**

```python
import json
from datetime import datetime
from pathlib import Path


def build_apollo_queries(intel: dict) -> list[dict]:
    """Build Apollo search parameters from company intel ICP."""
    icp = intel.get("ideal_customer_profile", {})
    titles = icp.get("decision_maker_titles", [])[:6]
    return [
        {
            "titles": titles,
            "employee_ranges": ["100,1000", "1000,10000"],
        }
    ]


def score_lead(person: dict, icp: dict) -> dict:
    """Score a lead 0-100 based on ICP alignment. Returns scores dict, total, and stars (1-5)."""
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
    """Filter to leads >= min_stars, sorted by total score desc, capped at max_leads."""
    qualified = [l for l in scored_leads if l["scoring"]["stars"] >= min_stars]
    qualified.sort(key=lambda l: l["scoring"]["total"], reverse=True)
    return qualified[:max_leads]


def save_leads(company_name: str, leads: list[dict], data_dir: str = "data") -> str:
    """Save leads to disk. Returns absolute file path."""
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
    """Load existing leads from disk. Returns None if not found."""
    filepath = Path(data_dir) / company_name.lower().replace(" ", "_") / "raw_leads.json"
    if not filepath.exists():
        return None
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("leads")
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_phase2.py -v
```

Expected: 20 passed

- [ ] **Step 5: Run all tests to confirm nothing broken**

```
pytest tests/ -v
```

Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add modules/phase2_prospecting.py tests/test_phase2.py
git commit -m "feat: add Phase 2 prospecting module with scoring, filtering, and save/load"
```

---

## Task 4: Google Sheets — Write Leads

**Files:**
- Modify: `utils/sheets.py` (add `write_leads`)
- Modify: `tests/test_sheets.py` (add 3 tests)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_sheets.py`:

```python
import gspread


def _mock_spreadsheet_with_missing_sheet(mock_sheet):
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_sheet
    mock_client = MagicMock()
    mock_client.open_by_key.return_value = mock_spreadsheet
    return mock_client, mock_spreadsheet, mock_sheet


def _sample_lead(stars=4, total=70):
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "title": "VP of CX",
        "email": "jane@acme.com",
        "email_status": "verified",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "company_industry": "Telecommunications",
        "company_employees": 5000,
        "scoring": {
            "stars": stars,
            "total": total,
            "scores": {
                "icp_fit": 20,
                "decision_maker": 25,
                "buying_signals": 20,
                "data_completeness": 5,
            },
        },
    }


def test_write_leads_creates_new_worksheet_if_missing():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_leads
    write_leads(mock_client, "fake_id", "Cresta", [_sample_lead()])
    mock_spreadsheet.add_worksheet.assert_called_once()


def test_write_leads_appends_header_row():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_leads
    write_leads(mock_client, "fake_id", "Cresta", [_sample_lead()])
    first_call_args = mock_sheet.append_row.call_args[0][0]
    assert "Stars" in first_call_args
    assert "Email" in first_call_args


def test_write_leads_appends_lead_data_rows():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_leads
    write_leads(mock_client, "fake_id", "Cresta", [_sample_lead(stars=4, total=70)])
    mock_sheet.append_rows.assert_called_once()
    rows = mock_sheet.append_rows.call_args[0][0]
    assert len(rows) == 1
    assert rows[0][0] == 4   # Stars
    assert rows[0][7] == "VP of CX"  # Title (index 7)
```

- [ ] **Step 2: Run new tests to confirm they fail**

```
pytest tests/test_sheets.py -v -k "write_leads"
```

Expected: 3 failed — `ImportError: cannot import name 'write_leads'`

- [ ] **Step 3: Add `write_leads` to `utils/sheets.py`**

Append this function to the bottom of `utils/sheets.py`:

```python
def write_leads(client: gspread.Client, spreadsheet_id: str,
                company_name: str, leads: list[dict]):
    """Write scored leads to a per-company leads tab in Google Sheets."""
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Leads"
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=18)

    sheet.clear()
    sheet.append_row([
        "Stars", "Total Score", "ICP Fit", "Decision Maker", "Buying Signals", "Data Completeness",
        "First Name", "Title", "Email", "Email Status",
        "LinkedIn URL", "Company", "Website", "Industry", "Employees", "Status",
    ])

    rows = []
    for lead in leads:
        scoring = lead.get("scoring", {})
        scores = scoring.get("scores", {})
        rows.append([
            scoring.get("stars", ""),
            scoring.get("total", ""),
            scores.get("icp_fit", ""),
            scores.get("decision_maker", ""),
            scores.get("buying_signals", ""),
            scores.get("data_completeness", ""),
            lead.get("first_name", ""),
            lead.get("title", ""),
            lead.get("email", ""),
            lead.get("email_status", ""),
            lead.get("linkedin_url", ""),
            lead.get("company_name", ""),
            lead.get("company_website", ""),
            lead.get("company_industry", ""),
            lead.get("company_employees", ""),
            "New",
        ])
    if rows:
        sheet.append_rows(rows)
```

- [ ] **Step 4: Run all sheets tests to confirm all pass**

```
pytest tests/test_sheets.py -v
```

Expected: 8 passed

- [ ] **Step 5: Run all tests**

```
pytest tests/ -v
```

Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add utils/sheets.py tests/test_sheets.py
git commit -m "feat: add write_leads to Google Sheets utility"
```

---

## Task 5: Orchestrator Phase 2 Integration

**Files:**
- Modify: `orchestrator.py`

No new tests here — orchestrator integration is covered by the end-to-end run in Task 6.

- [ ] **Step 1: Update imports at the top of `orchestrator.py`**

Replace the existing import block at the top of `orchestrator.py` with:

```python
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config
from modules.phase1_intel import build_scraping_tasks, prepare_claude_prompt, save_intel, load_intel
from modules.phase2_prospecting import build_apollo_queries, score_lead, filter_leads, save_leads, load_leads
from utils.apollo import search_people, extract_people
from utils.apify import get_client as get_apify_client, scrape_website, search_google
from utils.discord import phase_complete, phase_error
from utils.hunter import verify_email, find_email
from utils.sheets import (
    get_client as get_sheets_client,
    get_company,
    update_company_last_run,
    write_company_intel,
    write_leads,
)
```

- [ ] **Step 2: Add `run_phase2` function to `orchestrator.py`**

Add this function after `run_phase1` (before `main`):

```python
def run_phase2(company: dict, state: dict, resume: bool) -> list[dict] | None:
    """
    Searches Apollo for ICP-matched leads, scores them, verifies emails with Hunter,
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
    all_people = []

    for query in queries:
        label = ", ".join(query["titles"][:2])
        print(f"  Searching Apollo: {label[:70]}...")
        try:
            response = search_people(
                config.APOLLO_API_KEY,
                titles=query["titles"],
                employee_ranges=query["employee_ranges"],
                per_page=25,
            )
            people = extract_people(response)
            all_people.extend(people)
            print(f"    -> {len(people)} candidates found")
        except Exception as e:
            print(f"  WARNING: Apollo search failed: {e}")

    print(f"  Total candidates: {len(all_people)}")

    # Score all candidates
    scored = []
    for person in all_people:
        scoring = score_lead(person, icp)
        scored.append({**person, "scoring": scoring})

    # Filter to qualified leads
    leads = filter_leads(
        scored,
        min_stars=config.MIN_STAR_RATING_FOR_OUTREACH,
        max_leads=config.MAX_LEADS_PER_RUN,
    )
    print(f"  Qualified leads ({config.MIN_STAR_RATING_FOR_OUTREACH}+ stars): {len(leads)}")

    # Hunter.io email verification / finding
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
            domain = (
                lead["company_website"]
                .replace("https://", "")
                .replace("http://", "")
                .split("/")[0]
            )
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
    print(f"  Leads saved: {filepath} ({len(leads)} leads)")

    return leads
```

- [ ] **Step 3: Integrate Phase 2 into `main()`**

In `orchestrator.py`, find the Phase 1 block in `main()`:

```python
    # --- Phase 1 ---
    if not args.phase or args.phase == 1:
        intel = run_phase1(company, state, args.resume)
        ...
        print("  [OK] Phase 1 complete. Intel written to Google Sheets.")
```

Add the Phase 2 block immediately after it (before the `update_company_last_run` call):

```python
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
```

- [ ] **Step 4: Run all tests to confirm nothing broken**

```
pytest tests/ -v
```

Expected: all passed (imports will work since apollo/hunter/phase2 modules now exist)

- [ ] **Step 5: Commit**

```bash
git add orchestrator.py
git commit -m "feat: integrate Phase 2 prospecting into orchestrator with state tracking"
```

---

## Task 6: End-to-End Phase 2 Run — Cresta

This task validates the full Phase 2 pipeline with real APIs. No code changes — execution and verification only.

- [ ] **Step 1: Confirm Phase 1 is complete**

```
type data\cresta\state.json
```

Expected: `"completed_phases": ["phase1"]`

If not, run Phase 1 first: `python orchestrator.py --company Cresta --resume`

- [ ] **Step 2: Run Phase 2 for Cresta**

```
python orchestrator.py --company Cresta --phase 2
```

Expected output:
```
============================================================
PROJECT F — CRESTA
============================================================
Company: Cresta (https://cresta.com)
Completed phases: ['phase1']

============================================================
PHASE 2: PROSPECTING
============================================================
  Searching Apollo: VP of Customer Experience, VP of Contact Center Operations...
    -> 25 candidates found
  Total candidates: 25
  Qualified leads (3+ stars): X
  Verifying emails with Hunter.io...
  Leads saved: data\cresta\raw_leads.json (X leads)

  Writing leads to Google Sheets...
  [OK] Phase 2 complete. X leads written to Google Sheets.

Run complete. Completed phases: ['phase1', 'phase2']
```

If Apollo returns 0 candidates, see Troubleshooting below.

- [ ] **Step 3: Verify local files**

```
type data\cresta\state.json
```

Expected: `"completed_phases": ["phase1", "phase2"]`

```
python -c "import json; d=json.load(open('data/cresta/raw_leads.json')); print(d['_meta']); [print(l['name'], l['title'], l['scoring']['stars']) for l in d['leads'][:5]]"
```

Expected: prints meta and top 5 lead names with titles and star ratings.

- [ ] **Step 4: Verify Google Sheets**

Open the Google Spreadsheet:
- Tab "Cresta — Leads" should now exist with scored lead rows
- Each row has: Stars, Total Score, ICP Fit scores, First Name, Title, Email, LinkedIn, Company, Industry, Employees, Status=New

- [ ] **Step 5: Verify Discord notification**

Open Discord → Project F → #cresta-leads. Should see:
```
PHASE2 complete — Cresta
X leads scored and saved. Leads sheet updated.
```

- [ ] **Step 6: Test --resume skips Phase 2**

```
python orchestrator.py --company Cresta --resume
```

Expected: prints `[SKIP] Phase 2 already complete. Loading existing leads.` with no Apollo calls.

- [ ] **Step 7: Run full test suite**

```
pytest tests/ -v
```

Expected: all passed

- [ ] **Step 8: Final commit**

```bash
git add .
git commit -m "docs: verify Phase 2 end-to-end run complete for Cresta"
```

---

## Troubleshooting

**Apollo returns 0 results:**
Apollo's free plan may restrict People Search results. Check:
1. Log in to apollo.io → Search → People → try the same title filters manually
2. If the free tier is blocking API access, upgrade to Starter ($49/mo) or use the Apollo web UI to manually export a CSV, then load it as a static fixture in `data/cresta/raw_leads.json` in the format that `load_leads` expects

**Apollo returns people but all score < 3 stars:**
Lower `MIN_STAR_RATING_FOR_OUTREACH` to `2` in `.env` temporarily to see what's coming back. The scoring may need calibration based on real Apollo data.

**Hunter.io rate limit (429):**
Hunter free plan allows 25 verifications/month. The `except` block in `run_phase2` already catches this gracefully — leads will simply have no email status. Leads are still saved and written to Sheets.

**`write_leads` fails with gspread error:**
Verify the service account has Editor access to the Google Sheet. Check `credentials.json` path in `.env`.

---

## Verification Checklist

After Task 6 is complete, confirm:

- [ ] `pytest tests/ -v` — all tests pass (21 original + 6 apollo + 5 hunter + 20 phase2 + 3 sheets = 55 total)
- [ ] `data/cresta/raw_leads.json` — exists with leads and `_meta`
- [ ] `data/cresta/state.json` — shows `"completed_phases": ["phase1", "phase2"]`
- [ ] Google Sheet: "Cresta — Leads" tab populated with scored rows
- [ ] Discord #cresta-leads: Phase 2 notification received
- [ ] `--resume` skips Phase 2 correctly on second run
- [ ] Leads are sorted by score (highest first)
- [ ] All leads have `stars >= 3`

---

## What's Next (Phase 3 — After Phase 2 Validated)

Once Phase 2 produces a satisfactory leads list:
- `modules/phase3_scoring.py` — re-score leads with enriched signals from Apify company scrapes
- `modules/phase3_filtering.py` — final dedup, blacklist check, cap at 30 leads
- Integration into orchestrator

Or if scores are already good, skip enrichment and move directly to Phase 4 (outreach template generation).
