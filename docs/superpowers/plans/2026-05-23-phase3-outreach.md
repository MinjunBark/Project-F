# Phase 3 — Outreach Template Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a personalised cold email, call script, and LinkedIn message for each scored lead using Gemini 2.0 Flash, save to `data/cresta/outreach.json`, and write to a `"Cresta — Outreach"` Google Sheets tab via `python orchestrator.py --company Cresta --phase 3`.

**Architecture:** One Gemini API call per lead (all three formats in a single prompt). Signal pre-processing filters the lead's tech stack to Cresta-relevant tools and maps their industry to relevant pain points before building the prompt. Results flow: `modules/phase3_outreach.py` → `save_outreach()` → `utils/sheets.py write_outreach()`.

**Tech Stack:** `google-generativeai` SDK, `gemini-2.0-flash` model, existing `gspread` for Sheets, existing orchestrator/state pattern.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `utils/gemini.py` | Thin wrapper: configure API key, call model, return text |
| Create | `modules/phase3_outreach.py` | Prompt builder, response parser, generate + save + load |
| Create | `tests/test_gemini.py` | 2 tests for gemini util |
| Create | `tests/test_phase3.py` | 6 tests for phase3 module |
| Modify | `utils/sheets.py` | Append `write_outreach()` |
| Modify | `tests/test_sheets.py` | Append 3 tests for `write_outreach` |
| Modify | `config.py` | Add `GEMINI_API_KEY` |
| Modify | `orchestrator.py` | Add `run_phase3()` + Phase 3 block in `main()` |
| Modify | `requirements.txt` | Add `google-generativeai` |

---

## Task 1: Gemini Util

**Files:**
- Create: `utils/gemini.py`
- Create: `tests/test_gemini.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Install the package**

```bash
pip install google-generativeai
```

- [ ] **Step 2: Pin it in requirements.txt**

Add this line to `requirements.txt`:
```
google-generativeai>=0.8.0
```

- [ ] **Step 3: Write the failing tests**

Create `tests/test_gemini.py`:
```python
from unittest.mock import patch, MagicMock


def test_get_client_configures_api_key():
    with patch("utils.gemini.genai") as mock_genai:
        from utils import gemini
        gemini.get_client("test-key-123")
        mock_genai.configure.assert_called_once_with(api_key="test-key-123")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")


def test_generate_returns_text():
    mock_client = MagicMock()
    mock_client.generate_content.return_value.text = "hello world"
    from utils.gemini import generate
    result = generate(mock_client, "test prompt")
    assert result == "hello world"
    mock_client.generate_content.assert_called_once_with("test prompt")
```

- [ ] **Step 4: Run to confirm they fail**

```bash
pytest tests/test_gemini.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` — `utils.gemini` does not exist yet.

- [ ] **Step 5: Create `utils/gemini.py`**

```python
import google.generativeai as genai


def get_client(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def generate(client, prompt: str) -> str:
    return client.generate_content(prompt).text
```

- [ ] **Step 6: Run tests — confirm 2 pass**

```bash
pytest tests/test_gemini.py -v
```
Expected: `2 passed`

---

## Task 2: Phase 3 Outreach Module

**Files:**
- Create: `modules/phase3_outreach.py`
- Create: `tests/test_phase3.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_phase3.py`:
```python
from unittest.mock import MagicMock


SAMPLE_LEAD = {
    "first_name": "Jane",
    "last_name": "Doe",
    "title": "VP of Customer Experience",
    "company_name": "Acme Telecom",
    "company_industry": "Telecommunications",
    "company_employees": 500,
    "company_revenue": "120M",
    "company_technologies": "five9, salesforce, cisco, hubspot",
    "company_keywords": "contact center, customer service, telecom, support, voice, broadband",
}

SAMPLE_INTEL = {
    "market_positioning": {
        "value_proposition": "The only unified platform for human and AI agents.",
        "differentiators": [
            "Real-time AI guidance during live conversations",
            "Unified platform for autonomous AI and human agents",
            "Enterprise-grade compliance and guardrails",
        ],
    },
    "ideal_customer_profile": {
        "pain_points": [
            "High and rising cost-to-serve in contact centers",
            "Agent performance variability",
            "Manual QA limited to small sample of conversations",
            "Compliance risk from inconsistent agent behavior in regulated industries",
        ],
        "tech_stack_signals": ["Genesys", "Five9", "Salesforce", "Avaya"],
    },
}

SAMPLE_RESPONSE = """
[EMAIL_SUBJECT]
AI coaching for your Five9 contact center
[EMAIL_BODY]
Hi Jane, I noticed Acme Telecom runs Five9 across your contact center. Teams at your scale often struggle with agent performance variability and rising cost-to-serve. Cresta's real-time AI platform sits on top of Five9 and gives agents live guidance during calls. Would you be open to a 15-minute chat to see if it fits?
[CALL_SCRIPT]
Opener: Hi Jane, this is [name] from Cresta — we work with telecom contact centers running Five9. | Discovery Q1: How are you currently coaching agents between calls vs during live conversations? | Discovery Q2: What percentage of calls does your QA team actually review today? | Pitch: Cresta puts an AI coach on every call in real time — we've helped similar teams cut handle time by 20% and double QA coverage without adding headcount.
[LINKEDIN]
Hi Jane — saw Acme Telecom is scaling its contact center operations. Cresta helps telecom teams using Five9 cut handle time with real-time AI coaching. Would love to connect and share what we've seen work at similar companies.
[END]
"""


def test_build_outreach_prompt_includes_lead_identity():
    from modules.phase3_outreach import build_outreach_prompt
    prompt = build_outreach_prompt(SAMPLE_LEAD, SAMPLE_INTEL)
    assert "Jane Doe" in prompt
    assert "VP of Customer Experience" in prompt
    assert "Acme Telecom" in prompt


def test_build_outreach_prompt_includes_filtered_tech_signals():
    from modules.phase3_outreach import build_outreach_prompt
    prompt = build_outreach_prompt(SAMPLE_LEAD, SAMPLE_INTEL)
    assert "Five9" in prompt
    assert "Salesforce" in prompt


def test_build_outreach_prompt_omits_tech_line_when_no_match():
    from modules.phase3_outreach import build_outreach_prompt
    lead = {**SAMPLE_LEAD, "company_technologies": "shopify, wordpress, mailchimp"}
    prompt = build_outreach_prompt(lead, SAMPLE_INTEL)
    assert "Tech signals" not in prompt


def test_parse_outreach_response_extracts_all_fields():
    from modules.phase3_outreach import parse_outreach_response
    result = parse_outreach_response(SAMPLE_RESPONSE)
    assert "Five9" in result["email_subject"]
    assert "Jane" in result["email_body"]
    assert "Opener" in result["call_script"]
    assert "connect" in result["linkedin_message"]


def test_parse_outreach_response_returns_empty_on_malformed_input():
    from modules.phase3_outreach import parse_outreach_response
    result = parse_outreach_response("This has no delimiters at all.")
    assert result["email_subject"] == ""
    assert result["email_body"] == ""
    assert result["call_script"] == ""
    assert result["linkedin_message"] == ""
    assert "raw_response" in result


def test_generate_outreach_returns_required_keys():
    from modules.phase3_outreach import generate_outreach
    mock_gemini = MagicMock()
    mock_gemini.generate_content.return_value.text = SAMPLE_RESPONSE
    result = generate_outreach(mock_gemini, SAMPLE_LEAD, SAMPLE_INTEL)
    for key in ["email_subject", "email_body", "call_script", "linkedin_message"]:
        assert key in result
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_phase3.py -v
```
Expected: `ModuleNotFoundError` — `modules.phase3_outreach` does not exist yet.

- [ ] **Step 3: Create `modules/phase3_outreach.py`**

```python
import json
from datetime import datetime
from pathlib import Path

from utils.gemini import generate as _gemini_generate

_SIGNAL_KEYWORDS = {
    "genesys": "Genesys",
    "nice": "NICE",
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
    industry_lower = industry.lower()
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
    keywords = [k.strip() for k in (lead.get("company_keywords") or "").split(",")][:5]
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


def generate_outreach(gemini_client, lead: dict, intel: dict) -> dict:
    prompt = build_outreach_prompt(lead, intel)
    try:
        text = _gemini_generate(gemini_client, prompt)
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
```

- [ ] **Step 4: Run tests — confirm 6 pass**

```bash
pytest tests/test_phase3.py -v
```
Expected: `6 passed`

---

## Task 3: Sheets `write_outreach`

**Files:**
- Modify: `utils/sheets.py` (append function)
- Modify: `tests/test_sheets.py` (append 3 tests)

- [ ] **Step 1: Append the failing tests to `tests/test_sheets.py`**

Add at the bottom of `tests/test_sheets.py`:
```python
def _sample_outreach(stars=4):
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "title": "VP of CX",
        "email": "jane@acme.com",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "company_name": "Acme Corp",
        "company_industry": "Telecommunications",
        "scoring": {"stars": stars},
        "email_subject": "AI for your contact center",
        "email_body": "Hi Jane, Cresta helps telecom teams...",
        "call_script": "Opener | Q1 | Q2 | Pitch",
        "linkedin_message": "Hi Jane, would love to connect.",
    }


def test_write_outreach_creates_worksheet_when_missing():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_outreach
    write_outreach(mock_client, "fake_id", "Cresta", [_sample_outreach()])
    mock_spreadsheet.add_worksheet.assert_called_once()


def test_write_outreach_writes_correct_headers():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_outreach
    write_outreach(mock_client, "fake_id", "Cresta", [_sample_outreach()])
    headers = mock_sheet.append_row.call_args[0][0]
    assert headers[0] == "Company"
    assert "Email Subject" in headers
    assert "LinkedIn Message" in headers


def test_write_outreach_sorts_rows_by_stars_descending():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_outreach
    leads = [_sample_outreach(stars=3), _sample_outreach(stars=5), _sample_outreach(stars=4)]
    write_outreach(mock_client, "fake_id", "Cresta", leads)
    rows = mock_sheet.append_rows.call_args[0][0]
    # Stars is column index 7: Company(0) Industry(1) First(2) Last(3) Title(4) Email(5) LinkedIn(6) Stars(7)
    assert rows[0][7] == 5
    assert rows[1][7] == 4
    assert rows[2][7] == 3
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_sheets.py::test_write_outreach_creates_worksheet_when_missing tests/test_sheets.py::test_write_outreach_writes_correct_headers tests/test_sheets.py::test_write_outreach_sorts_rows_by_stars_descending -v
```
Expected: `AttributeError` — `write_outreach` does not exist yet.

- [ ] **Step 3: Append `write_outreach` to `utils/sheets.py`**

Add at the bottom of `utils/sheets.py`:
```python
def write_outreach(client: gspread.Client, spreadsheet_id: str,
                   company_name: str, results: list[dict]):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Outreach"
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=12)

    sheet.clear()
    sheet.append_row([
        "Company", "Industry", "First Name", "Last Name", "Title",
        "Email", "LinkedIn URL", "Stars", "Email Subject", "Email Body",
        "Call Script", "LinkedIn Message",
    ])

    sorted_results = sorted(results, key=lambda r: r.get("scoring", {}).get("stars", 0), reverse=True)
    rows = [
        [
            r.get("company_name", ""),
            r.get("company_industry", ""),
            r.get("first_name", ""),
            r.get("last_name", ""),
            r.get("title", ""),
            r.get("email", ""),
            r.get("linkedin_url", ""),
            r.get("scoring", {}).get("stars", ""),
            r.get("email_subject", ""),
            r.get("email_body", ""),
            r.get("call_script", ""),
            r.get("linkedin_message", ""),
        ]
        for r in sorted_results
    ]
    if rows:
        sheet.append_rows(rows)
```

- [ ] **Step 4: Run full sheets tests — confirm 11 pass**

```bash
pytest tests/test_sheets.py -v
```
Expected: `11 passed`

---

## Task 4: Config + Orchestrator Integration

**Files:**
- Modify: `config.py`
- Modify: `orchestrator.py`

- [ ] **Step 1: Add `GEMINI_API_KEY` to `config.py`**

Add this line at the end of `config.py`:
```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

- [ ] **Step 2: Update imports in `orchestrator.py`**

Add `import time` to the stdlib imports block (line 1–6):
```python
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
```

Add to the project imports block (after existing module imports):
```python
from utils.gemini import get_client as get_gemini_client
from modules.phase3_outreach import generate_outreach, save_outreach, load_outreach
```

Update the `write_leads` import line to also include `write_outreach`:
```python
from utils.sheets import (
    get_client as get_sheets_client,
    get_company,
    update_company_last_run,
    write_company_intel,
    write_leads,
    write_outreach,
)
```

- [ ] **Step 3: Add `run_phase3` to `orchestrator.py`**

Add this function after `run_phase2`, before `main()`:
```python
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
```

- [ ] **Step 4: Add Phase 3 block in `main()`**

Add this block after the Phase 2 block (after the `update_company_last_run` call is still last):
```python
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
```

- [ ] **Step 5: Run full test suite — confirm 77 pass**

```bash
pytest --tb=short -q
```
Expected: `77 passed`

---

## Task 5: End-to-End Run

- [ ] **Step 1: Confirm prerequisites**

```bash
python -c "import google.generativeai; print('SDK OK')"
python -c "import config; print('GEMINI_API_KEY set:', bool(config.GEMINI_API_KEY))"
```
Both must print without error. If `GEMINI_API_KEY` is not set, check `.env`.

- [ ] **Step 2: Run Phase 3**

```bash
python orchestrator.py --company Cresta --phase 3
```

Expected console output:
```
============================================================
PROJECT F — CRESTA
============================================================
Company: Cresta (https://cresta.com)
Completed phases: ['phase1', 'phase2']

============================================================
PHASE 3: OUTREACH GENERATION
============================================================
  [1/30] Melanie Hannasch @ Vyvebb.com...
  [2/30] Tom Wicker @ Healthplanone...
  ...
  [30/30] ...
  Outreach saved: data\cresta\outreach.json (30 entries)

  Writing outreach to Google Sheets...
  [OK] Phase 3 complete. 30 outreach templates written to Google Sheets.

Run complete. Completed phases: ['phase1', 'phase2', 'phase3']
```

- [ ] **Step 3: Verify local output**

```bash
python -c "
import json
data = json.load(open('data/cresta/outreach.json'))
first = data['outreach'][0]
print('Total:', data['_meta']['total'])
print('Keys:', list(first.keys()))
print('Subject:', first.get('email_subject', '(missing)'))
print('Body preview:', first.get('email_body', '')[:80])
"
```
Expected: `Total: 30`, all four generated fields present and non-empty.

- [ ] **Step 4: Verify Google Sheets**

Open the spreadsheet and confirm:
- A `"Cresta — Outreach"` tab exists
- Row 1 is: `Company | Industry | First Name | Last Name | Title | Email | LinkedIn URL | Stars | Email Subject | Email Body | Call Script | LinkedIn Message`
- Rows are sorted highest stars first
- 30 data rows present

- [ ] **Step 5: Verify state**

```bash
python -c "import json; s=json.load(open('data/cresta/state.json')); print(s['completed_phases'])"
```
Expected: `['phase1', 'phase2', 'phase3']`
