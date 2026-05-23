# Project F — Phase 1: Company Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full project foundation and Phase 1 Company Intelligence module — scrapes a selected client company (e.g., Cresta), outputs structured intel JSON, and syncs to Google Sheets.

**Architecture:** Modular Python pipeline (Option B). Phase 1 scrapes the client company using Apify, saves raw data, then prints a structured prompt for Claude Code to analyze interactively. The resulting JSON is saved locally and written to Google Sheet 2. Discord notifies on completion.

**Tech Stack:** Python 3.11+, pytest, gspread, google-auth, apify-client, requests, python-dotenv

---

## Pre-requisites: Manual Setup Steps (User Does These First)

Before any code runs, the user must complete these one-time setups. Claude Code provides instructions at each step.

### A. Google Cloud + Sheets API Setup
1. Go to console.cloud.google.com → Create new project: "Project F"
2. Enable APIs: search "Google Sheets API" → Enable
3. Go to IAM & Admin → Service Accounts → Create Service Account
   - Name: `project-f-sheets`
   - Role: Editor
4. Click the service account → Keys tab → Add Key → JSON → Download
5. Save the downloaded file as `credentials.json` in the project root
6. Go to your Google Sheets spreadsheet → Share → paste the service account email (from the JSON file, field `client_email`) → give Editor access
7. Copy the Spreadsheet ID from the URL: `docs.google.com/spreadsheets/d/[THIS_IS_THE_ID]/edit`

### B. API Accounts to Create
| Service | URL | What to get |
|---|---|---|
| Apify | apify.com | API Token (Settings → Integrations) |
| Apollo.io | apollo.io | API Key (Settings → Integrations) — Phase 2, get now |
| Hunter.io | hunter.io | API Key (Dashboard → API) — Phase 3, get now |
| Discord | discord.com | Create "Project F" server → each channel → Edit Channel → Integrations → Webhooks → Copy URL |

### C. Google Sheets Structure to Create Manually
Create one Google Spreadsheet with these tabs:
- Tab 1: `Company List` — columns: `Company Name`, `Website`, `Status`, `Last Run Date`, `Total Runs`, `Notes`
- Add first row of data: `Cresta`, `https://cresta.com`, `Active`, _(blank)_, `0`, _(blank)_

### D. Discord Server Setup
Create server "Project F" with channels:
`#announcements`, `#lead-gen-updates`, `#cresta-leads`, `#feedback`, `#scoring-decisions`, `#system-logs`
Create one webhook per channel. Copy all webhook URLs into `.env`.

---

## File Map

```
Project-F/
  .env                          ← secrets (never committed)
  .env.example                  ← template for teammates
  .gitignore
  requirements.txt
  config.py                     ← loads .env, exports constants
  orchestrator.py               ← CLI entry point, coordinates phases
  credentials.json              ← Google service account (never committed)
  modules/
    __init__.py
    phase1_intel.py             ← scraping tasks, prompt builder, save/load intel
  utils/
    __init__.py
    sheets.py                   ← Google Sheets read/write wrapper
    discord.py                  ← Discord webhook notifications
    apify.py                    ← Apify scraping wrapper
  tests/
    __init__.py
    test_sheets.py
    test_discord.py
    test_phase1.py
  data/
    cresta/
      state.json                ← auto-created by orchestrator
      phase1_raw.json           ← auto-created by phase1_intel.py
      phase1_prompt.txt         ← auto-created, paste to Claude Code
      company_intel.json        ← human saves this after Claude Code analysis
  docs/
    superpowers/
      specs/2026-05-22-project-f-lead-gen-design.md
      plans/2026-05-22-phase1-implementation.md
    diagrams/project-f-architecture.html
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `config.py`
- Create: `modules/__init__.py`
- Create: `utils/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `.gitignore`**

```
.env
credentials.json
data/
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 2: Create `.env.example`**

```
# Google Sheets
GOOGLE_CREDENTIALS_PATH=credentials.json
SPREADSHEET_ID=your_spreadsheet_id_here

# Apify
APIFY_TOKEN=your_apify_token_here

# Apollo.io (Phase 2)
APOLLO_API_KEY=your_apollo_key_here

# Hunter.io (Phase 3)
HUNTER_API_KEY=your_hunter_key_here

# Discord Webhooks
DISCORD_WEBHOOK_UPDATES=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_LEADS=https://discord.com/api/webhooks/...
DISCORD_WEBHOOK_LOGS=https://discord.com/api/webhooks/...

# Settings
MAX_LEADS_PER_RUN=30
MIN_STAR_RATING_FOR_OUTREACH=3
```

- [ ] **Step 3: Create `requirements.txt`**

```
gspread==6.1.2
google-auth==2.29.0
apify-client==1.8.1
requests==2.32.3
python-dotenv==1.0.1
pytest==8.2.0
pytest-mock==3.14.0
```

- [ ] **Step 4: Create `config.py`**

```python
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")
DISCORD_WEBHOOK_UPDATES = os.getenv("DISCORD_WEBHOOK_UPDATES", "")
DISCORD_WEBHOOK_LEADS = os.getenv("DISCORD_WEBHOOK_LEADS", "")
DISCORD_WEBHOOK_LOGS = os.getenv("DISCORD_WEBHOOK_LOGS", "")
MAX_LEADS_PER_RUN = int(os.getenv("MAX_LEADS_PER_RUN", "30"))
MIN_STAR_RATING_FOR_OUTREACH = int(os.getenv("MIN_STAR_RATING_FOR_OUTREACH", "3"))
```

- [ ] **Step 5: Create empty `__init__.py` files**

Create empty files at: `modules/__init__.py`, `utils/__init__.py`, `tests/__init__.py`

- [ ] **Step 6: Install dependencies**

```
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 7: Copy `.env.example` to `.env` and fill in values**

User fills in all values from their Pre-requisite setup (API keys, webhook URLs, spreadsheet ID).

- [ ] **Step 8: Commit**

```bash
git init
git add .gitignore .env.example requirements.txt config.py modules/__init__.py utils/__init__.py tests/__init__.py
git commit -m "feat: initialize Project F scaffold"
```

---

## Task 2: Google Sheets Utility

**Files:**
- Create: `utils/sheets.py`
- Create: `tests/test_sheets.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_sheets.py`:

```python
import pytest
from unittest.mock import MagicMock

def _mock_client(records):
    mock_sheet = MagicMock()
    mock_sheet.get_all_records.return_value = records
    mock_client = MagicMock()
    mock_client.open_by_key.return_value.worksheet.return_value = mock_sheet
    return mock_client, mock_sheet

def test_read_company_list_returns_active_only():
    records = [
        {"Company Name": "Cresta", "Website": "https://cresta.com", "Status": "Active",
         "Last Run Date": "", "Total Runs": 0, "Notes": ""},
        {"Company Name": "OldCo", "Website": "https://oldco.com", "Status": "Paused",
         "Last Run Date": "", "Total Runs": 0, "Notes": ""},
    ]
    mock_client, _ = _mock_client(records)
    from utils.sheets import read_company_list
    result = read_company_list(mock_client, "fake_id")
    assert len(result) == 1
    assert result[0]["Company Name"] == "Cresta"

def test_get_company_found():
    records = [{"Company Name": "Cresta", "Website": "https://cresta.com",
                "Status": "Active", "Last Run Date": "", "Total Runs": 0, "Notes": ""}]
    mock_client, _ = _mock_client(records)
    from utils.sheets import get_company
    result = get_company(mock_client, "fake_id", "Cresta")
    assert result is not None
    assert result["Company Name"] == "Cresta"

def test_get_company_not_found():
    records = [{"Company Name": "Cresta", "Website": "https://cresta.com",
                "Status": "Active", "Last Run Date": "", "Total Runs": 0, "Notes": ""}]
    mock_client, _ = _mock_client(records)
    from utils.sheets import get_company
    result = get_company(mock_client, "fake_id", "NonExistent")
    assert result is None

def test_get_company_case_insensitive():
    records = [{"Company Name": "Cresta", "Website": "https://cresta.com",
                "Status": "Active", "Last Run Date": "", "Total Runs": 0, "Notes": ""}]
    mock_client, _ = _mock_client(records)
    from utils.sheets import get_company
    result = get_company(mock_client, "fake_id", "cresta")
    assert result is not None

def test_read_company_list_default_active_when_no_status():
    records = [{"Company Name": "Cresta", "Website": "https://cresta.com",
                "Status": "Active", "Last Run Date": "", "Total Runs": 0, "Notes": ""}]
    mock_client, _ = _mock_client(records)
    from utils.sheets import read_company_list
    result = read_company_list(mock_client, "fake_id")
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_sheets.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.sheets'`

- [ ] **Step 3: Create `utils/sheets.py`**

```python
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def read_company_list(client: gspread.Client, spreadsheet_id: str) -> list[dict]:
    sheet = client.open_by_key(spreadsheet_id).worksheet("Company List")
    records = sheet.get_all_records()
    return [r for r in records if r.get("Status", "Active") == "Active"]


def get_company(client: gspread.Client, spreadsheet_id: str, company_name: str) -> dict | None:
    companies = read_company_list(client, spreadsheet_id)
    for c in companies:
        if c["Company Name"].lower() == company_name.lower():
            return c
    return None


def update_company_last_run(client: gspread.Client, spreadsheet_id: str, company_name: str):
    sheet = client.open_by_key(spreadsheet_id).worksheet("Company List")
    records = sheet.get_all_records()
    headers = list(records[0].keys()) if records else []
    for i, record in enumerate(records, start=2):
        if record["Company Name"].lower() == company_name.lower():
            date_col = headers.index("Last Run Date") + 1
            runs_col = headers.index("Total Runs") + 1
            sheet.update_cell(i, date_col, datetime.now().strftime("%Y-%m-%d"))
            sheet.update_cell(i, runs_col, int(record.get("Total Runs", 0)) + 1)
            return


def write_company_intel(client: gspread.Client, spreadsheet_id: str,
                        company_name: str, intel: dict):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Intelligence"
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=150, cols=2)

    sheet.clear()
    sheet.append_row(["Field", "Value"])
    rows = []
    for section, fields in intel.items():
        if section == "_meta":
            continue
        rows.append([f"=== {section.upper().replace('_', ' ')} ===", ""])
        if isinstance(fields, dict):
            for field, value in fields.items():
                display = ", ".join(value) if isinstance(value, list) else str(value)
                rows.append([field.replace("_", " ").title(), display])
        elif isinstance(fields, list):
            rows.append([section.replace("_", " ").title(), ", ".join(str(v) for v in fields)])
        else:
            rows.append([section.replace("_", " ").title(), str(fields)])
    sheet.append_rows(rows)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_sheets.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add utils/sheets.py tests/test_sheets.py
git commit -m "feat: add Google Sheets utility with read/write wrappers"
```

---

## Task 3: Discord Webhook Utility

**Files:**
- Create: `utils/discord.py`
- Create: `tests/test_discord.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_discord.py`:

```python
import pytest
from unittest.mock import patch, MagicMock

def _mock_post(status_code=204):
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock

def test_phase_complete_sends_embed():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_complete
        phase_complete("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Intel built")
        payload = mock_post.call_args[1]["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

def test_phase_complete_message_contains_company():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_complete
        phase_complete("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Intel built")
        payload = mock_post.call_args[1]["json"]
        assert "Cresta" in payload["embeds"][0]["description"]

def test_phase_error_message_contains_error():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_error
        phase_error("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Timeout error")
        payload = mock_post.call_args[1]["json"]
        assert "Timeout error" in payload["embeds"][0]["description"]
        assert "failed" in payload["embeds"][0]["description"].lower()

def test_color_for_known_phases():
    from utils.discord import _color_for_phase
    assert _color_for_phase("phase1") == 0x1abc9c
    assert _color_for_phase("phase2") == 0x9b59b6
    assert _color_for_phase("error") == 0xff0000

def test_color_for_unknown_phase_returns_default():
    from utils.discord import _color_for_phase
    assert _color_for_phase("unknown") == 0x95a5a6
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_discord.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.discord'`

- [ ] **Step 3: Create `utils/discord.py`**

```python
import requests
from datetime import datetime


def _color_for_phase(phase: str) -> int:
    return {
        "phase1": 0x1abc9c,
        "phase2": 0x9b59b6,
        "phase3": 0xf39c12,
        "phase4": 0x2980b9,
        "phase5": 0xe74c3c,
        "error":  0xff0000,
    }.get(phase, 0x95a5a6)


def send_notification(webhook_url: str, message: str, phase: str = "info") -> int:
    payload = {
        "embeds": [{
            "description": message,
            "color": _color_for_phase(phase),
            "footer": {"text": f"Project F · {datetime.now().strftime('%Y-%m-%d %H:%M')}"}
        }]
    }
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()
    return response.status_code


def phase_complete(webhook_url: str, phase: str, company: str, summary: str) -> int:
    message = f"✓ **{phase.upper()} complete** — {company}\n{summary}"
    return send_notification(webhook_url, message, phase)


def phase_error(webhook_url: str, phase: str, company: str, error: str) -> int:
    message = f"❌ **{phase.upper()} failed** — {company}\n```{error}```"
    return send_notification(webhook_url, message, "error")
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_discord.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add utils/discord.py tests/test_discord.py
git commit -m "feat: add Discord webhook utility for phase notifications"
```

---

## Task 4: Apify Scraping Utility

**Files:**
- Create: `utils/apify.py`

Note: Apify makes live HTTP calls — no unit tests here. Integration tested in Task 7 end-to-end run.

- [ ] **Step 1: Create `utils/apify.py`**

```python
from apify_client import ApifyClient


def get_client(api_token: str) -> ApifyClient:
    return ApifyClient(api_token)


def scrape_website(client: ApifyClient, url: str, max_pages: int = 10) -> list[dict]:
    """Crawl a website and return list of {url, title, text} dicts."""
    run = client.actor("apify/website-content-crawler").call(run_input={
        "startUrls": [{"url": url}],
        "maxCrawlPages": max_pages,
        "crawlerType": "cheerio",
    })
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        results.append({
            "url": item.get("url", ""),
            "title": item.get("metadata", {}).get("title", ""),
            "text": item.get("text", "")[:3000],
        })
    return results


def search_google_news(client: ApifyClient, query: str, max_results: int = 5) -> list[dict]:
    """Search Google and return list of {title, url, description} dicts."""
    run = client.actor("apify/google-search-scraper").call(run_input={
        "queries": [query],
        "maxResultsPerQuery": max_results,
        "countryCode": "us",
    })
    results = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        for r in item.get("organicResults", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("description", ""),
            })
    return results
```

- [ ] **Step 2: Commit**

```bash
git add utils/apify.py
git commit -m "feat: add Apify scraping utility for website crawling and news search"
```

---

## Task 5: Phase 1 Intel Module

**Files:**
- Create: `modules/phase1_intel.py`
- Create: `tests/test_phase1.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_phase1.py`:

```python
import pytest
import json
from pathlib import Path


def test_build_scraping_tasks_returns_five_tasks():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    assert len(tasks) == 5


def test_build_scraping_tasks_includes_main_website():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    urls = [t.get("url", "") for t in tasks if t["type"] == "website"]
    assert "https://cresta.com" in urls


def test_build_scraping_tasks_news_queries_contain_company():
    from modules.phase1_intel import build_scraping_tasks
    tasks = build_scraping_tasks("Cresta", "https://cresta.com")
    news_tasks = [t for t in tasks if t["type"] == "news"]
    assert len(news_tasks) >= 2
    for task in news_tasks:
        assert "Cresta" in task["query"]


def test_prepare_claude_prompt_contains_company_name():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta AI", "text": "Real-time coaching."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    assert "Cresta" in prompt


def test_prepare_claude_prompt_contains_all_schema_keys():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta", "text": "Contact center AI."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    for key in ["company_profile", "products_services", "market_positioning",
                "ideal_customer_profile", "competitor_analysis",
                "warm_lead_signals", "content_intelligence"]:
        assert key in prompt, f"Schema key missing from prompt: {key}"


def test_prepare_claude_prompt_instructs_json_only():
    from modules.phase1_intel import prepare_claude_prompt
    scraped = [{"url": "https://cresta.com", "title": "Cresta", "text": "AI platform."}]
    prompt = prepare_claude_prompt("Cresta", scraped)
    assert "Return ONLY the JSON" in prompt


def test_save_intel_creates_json_file(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta", "website": "cresta.com"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    assert Path(filepath).exists()


def test_save_intel_content_is_correct(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    with open(filepath) as f:
        saved = json.load(f)
    assert saved["company_profile"]["name"] == "Cresta"


def test_save_intel_adds_meta(tmp_path):
    from modules.phase1_intel import save_intel
    intel = {"company_profile": {"name": "Cresta"}}
    filepath = save_intel("Cresta", intel, data_dir=str(tmp_path))
    with open(filepath) as f:
        saved = json.load(f)
    assert "_meta" in saved
    assert saved["_meta"]["company"] == "Cresta"
    assert saved["_meta"]["generated_by"] == "Claude Code (interactive)"


def test_load_intel_returns_none_if_missing(tmp_path):
    from modules.phase1_intel import load_intel
    assert load_intel("NonExistent", data_dir=str(tmp_path)) is None


def test_load_intel_round_trips_data(tmp_path):
    from modules.phase1_intel import save_intel, load_intel
    intel = {"company_profile": {"name": "Cresta"}}
    save_intel("Cresta", intel, data_dir=str(tmp_path))
    loaded = load_intel("Cresta", data_dir=str(tmp_path))
    assert loaded["company_profile"]["name"] == "Cresta"
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_phase1.py -v
```

Expected: `ModuleNotFoundError: No module named 'modules.phase1_intel'`

- [ ] **Step 3: Create `modules/phase1_intel.py`**

```python
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
```

- [ ] **Step 4: Run tests to confirm they pass**

```
pytest tests/test_phase1.py -v
```

Expected: 11 passed

- [ ] **Step 5: Run all tests to confirm nothing broken**

```
pytest tests/ -v
```

Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add modules/phase1_intel.py tests/test_phase1.py
git commit -m "feat: add Phase 1 company intel module with scraping tasks and prompt builder"
```

---

## Task 6: Orchestrator Foundation

**Files:**
- Create: `orchestrator.py`

- [ ] **Step 1: Create `orchestrator.py`**

```python
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config
from modules.phase1_intel import build_scraping_tasks, prepare_claude_prompt, save_intel, load_intel
from utils.apify import get_client as get_apify_client, scrape_website, search_google_news
from utils.discord import phase_complete, phase_error
from utils.sheets import get_client as get_sheets_client, get_company, update_company_last_run, write_company_intel


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
    Returns intel dict if complete, or None if Claude Code action is required.
    When None is returned, the orchestrator should stop and instruct the user.
    """
    company_name = company["Company Name"]

    if resume and "phase1" in state["completed_phases"]:
        existing = load_intel(company_name)
        if existing:
            print("  [SKIP] Phase 1 complete. Loading existing intel.")
            return existing

    print("\n" + "=" * 60)
    print("PHASE 1: COMPANY INTELLIGENCE")
    print("=" * 60)

    # Check if intel already exists from a previous partial run
    existing = load_intel(company_name)
    if existing and not resume:
        print(f"  Intel file found for {company_name}. Use --resume to skip Phase 1.")

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
            elif task["type"] == "news":
                results = search_google_news(apify, task["query"])
                scraped_data.extend(results)
        except Exception as e:
            print(f"  WARNING: scrape failed for {label[:60]}: {e}")

    # Save raw data
    company_dir = Path("data") / company_name.lower().replace(" ", "_")
    company_dir.mkdir(parents=True, exist_ok=True)

    raw_path = company_dir / "phase1_raw.json"
    with open(raw_path, "w") as f:
        json.dump(scraped_data, f, indent=2)

    # Build and save prompt
    prompt = prepare_claude_prompt(company_name, scraped_data)
    prompt_path = company_dir / "phase1_prompt.txt"
    with open(prompt_path, "w") as f:
        f.write(prompt)

    print(f"\n  Raw data saved:  {raw_path}  ({len(scraped_data)} pages)")
    print(f"  Prompt saved:    {prompt_path}")
    print("\n" + "=" * 60)
    print("ACTION REQUIRED — Claude Code Analysis")
    print("=" * 60)
    print(f"1. Open: {prompt_path}")
    print("2. Paste the full prompt to Claude Code")
    print("3. Save Claude Code's JSON response to:")
    print(f"   data/{company_name.lower()}/company_intel.json")
    print(f"4. Re-run: python orchestrator.py --company {company_name} --resume")
    print("=" * 60)

    return None  # Signals human action required


def main():
    parser = argparse.ArgumentParser(description="Project F Lead Generation Orchestrator")
    parser.add_argument("--company", required=True, help="Company name (must match Company List sheet)")
    parser.add_argument("--resume", action="store_true", help="Skip completed phases")
    parser.add_argument("--feedback", action="store_true", help="Run Phase 5 feedback processing")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific phase only")
    args = parser.parse_args()

    print(f"\n{'=' * 60}")
    print(f"PROJECT F — {args.company.upper()}")
    print(f"{'=' * 60}")

    # Validate company exists in sheet
    sheets = get_sheets_client(config.GOOGLE_CREDENTIALS_PATH)
    company = get_company(sheets, config.SPREADSHEET_ID, args.company)

    if not company:
        print(f"ERROR: '{args.company}' not found in Company List sheet.")
        sys.exit(1)

    if company.get("Status", "Active") != "Active":
        print(f"ERROR: '{args.company}' is Paused. Update Status to Active to run.")
        sys.exit(1)

    print(f"Company: {company['Company Name']} ({company['Website']})")
    state = load_state(args.company)

    # Phase 1
    if not args.phase or args.phase == 1:
        intel = run_phase1(company, state, args.resume)
        if intel is None:
            print("\nRun paused — waiting for Claude Code analysis.")
            return

        # Check if intel was loaded from file (resume path) or just generated
        if "phase1" not in state["completed_phases"]:
            write_company_intel(sheets, config.SPREADSHEET_ID, company["Company Name"], intel)
            state["completed_phases"].append("phase1")
            save_state(args.company, state)
            if config.DISCORD_WEBHOOK_UPDATES:
                phase_complete(config.DISCORD_WEBHOOK_UPDATES, "phase1", args.company,
                               f"Intel built — ICP extracted. Sheet 2 updated.")
            print("\n✓ Phase 1 complete. Intel written to Google Sheets.")

    update_company_last_run(sheets, config.SPREADSHEET_ID, args.company)
    print(f"\nRun complete. State: {state['completed_phases']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add orchestrator.py
git commit -m "feat: add orchestrator with phase coordination, state management, and resume support"
```

---

## Task 7: End-to-End Phase 1 Run — Cresta

This task validates the full Phase 1 pipeline works with real APIs. No code changes — this is execution and verification.

- [ ] **Step 1: Verify all pre-requisites are complete**

Confirm:
- `credentials.json` exists in project root
- `.env` has `SPREADSHEET_ID`, `APIFY_TOKEN`, `DISCORD_WEBHOOK_UPDATES` filled in
- Google Sheet "Company List" tab has Cresta row
- Discord "Project F" server is created with `#lead-gen-updates` channel and webhook configured

- [ ] **Step 2: Run Phase 1 for Cresta**

```
python orchestrator.py --company Cresta
```

Expected output:
```
============================================================
PROJECT F — CRESTA
============================================================
Company: Cresta (https://cresta.com)

============================================================
PHASE 1: COMPANY INTELLIGENCE
============================================================
  Scraping: https://cresta.com...
  Scraping: https://cresta.com/blog...
  Scraping: Cresta funding news 2025 2026...
  Scraping: Cresta customer case study results...
  Scraping: Cresta competitors comparison alternative...

  Raw data saved:  data/cresta/phase1_raw.json  (XX pages)
  Prompt saved:    data/cresta/phase1_prompt.txt

============================================================
ACTION REQUIRED — Claude Code Analysis
============================================================
1. Open: data/cresta/phase1_prompt.txt
2. Paste the full prompt to Claude Code
3. Save Claude Code's JSON response to:
   data/cresta/company_intel.json
4. Re-run: python orchestrator.py --company Cresta --resume
============================================================

Run paused — waiting for Claude Code analysis.
```

- [ ] **Step 3: Claude Code analysis (interactive)**

Open `data/cresta/phase1_prompt.txt`, paste its full contents to Claude Code in this conversation. Claude Code returns structured JSON. Save that JSON to `data/cresta/company_intel.json`.

- [ ] **Step 4: Resume Phase 1 with the intel file saved**

```
python orchestrator.py --company Cresta --resume
```

Expected output:
```
  [SKIP] Phase 1 complete. Loading existing intel.
✓ Phase 1 complete. Intel written to Google Sheets.
Run complete. State: ['phase1']
```

- [ ] **Step 5: Verify Google Sheets was updated**

Open the Google Spreadsheet:
- Sheet 1 "Company List": Cresta row should have today's date in "Last Run Date" and `1` in "Total Runs"
- Sheet 2 "Cresta — Intelligence": should be populated with Field | Value rows grouped by section

- [ ] **Step 6: Verify Discord notification was received**

Open Discord → Project F server → #lead-gen-updates. Should see:
```
✓ PHASE1 complete — Cresta
Intel built — ICP extracted. Sheet 2 updated.
```

- [ ] **Step 7: Verify local state**

```
type data\cresta\state.json
```

Expected:
```json
{
  "company": "Cresta",
  "completed_phases": ["phase1"],
  "started_at": "2026-..."
}
```

- [ ] **Step 8: Final all-tests run**

```
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 9: Save plan copy to project docs**

```bash
copy "C:\Users\alex8\.claude\plans\how-do-i-open-logical-moon.md" "C:\Users\alex8\Documents\Project F\docs\superpowers\plans\2026-05-22-phase1-implementation.md"
```

- [ ] **Step 10: Final commit**

```bash
git add docs/superpowers/plans/
git commit -m "docs: add Phase 1 implementation plan"
```

---

## Verification Checklist

After Task 7 is complete, confirm all of the following:

- [ ] `pytest tests/ -v` — all tests pass
- [ ] `data/cresta/phase1_raw.json` — exists and has scraped content
- [ ] `data/cresta/phase1_prompt.txt` — exists with full analysis prompt
- [ ] `data/cresta/company_intel.json` — exists with all 7 schema sections populated
- [ ] `data/cresta/state.json` — shows `"completed_phases": ["phase1"]`
- [ ] Google Sheet 1: Cresta Last Run Date updated, Total Runs = 1
- [ ] Google Sheet 2: "Cresta — Intelligence" tab populated with structured intel
- [ ] Discord #lead-gen-updates: Phase 1 completion notification received
- [ ] Orchestrator `--resume` flag skips Phase 1 correctly on second run

---

## What's Next (Phase 2 Plan — After Phase 1 Validated)

Once Phase 1 passes all verification checks and the Cresta intel is reviewed and satisfactory, the Phase 2 plan will cover:
- `utils/apollo.py` — Apollo API wrapper for lead finding
- `utils/hunter.py` — Hunter.io email verification
- `modules/phase2_prospecting.py` — ICP-driven Apollo search + Apify enrichment per lead
- Integration into orchestrator
- End-to-end prospecting run for Cresta (15–30 leads)
