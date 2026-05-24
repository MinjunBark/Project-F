# Phase 3 — Outreach Template Generation

**Date:** 2026-05-23  
**Status:** Approved

## Summary

Generate three personalized outreach formats (cold email, call script, LinkedIn message) for each scored lead using the Gemini API. Results are saved locally as JSON and written to a new Google Sheets tab. Triggered via the existing orchestrator: `python orchestrator.py --company Cresta --phase 3`.

---

## Architecture

```
orchestrator.py --phase 3
    └── run_phase3(company, state, resume)
            ├── load_intel(company_name)           # existing
            ├── load_leads(company_name)            # existing
            ├── utils/gemini.py → get_client()
            ├── modules/phase3_outreach.py
            │       ├── build_outreach_prompt(lead, intel)
            │       ├── generate_outreach(gemini, lead, intel)   ← 1 API call/lead
            │       ├── parse_outreach_response(text)
            │       └── save_outreach(company_name, results)    → data/{company}/outreach.json
            └── utils/sheets.py → write_outreach()              → "{Company} — Outreach" tab
```

**New files:** `utils/gemini.py`, `modules/phase3_outreach.py`  
**Modified:** `orchestrator.py`, `utils/sheets.py`, `config.py`  
**Tests:** `tests/test_gemini.py`, `tests/test_phase3.py` (append 3 tests to `tests/test_sheets.py`)

---

## New Files

### `utils/gemini.py`

Thin wrapper around the `google-generativeai` SDK.

```python
def get_client(api_key: str) -> GenerativeModel
def generate(client: GenerativeModel, prompt: str) -> str
```

Model: `gemini-2.0-flash`. At 30 leads × 1 call each = 30 requests, well within the free tier (1,500 req/day, 15 req/min). Expected runtime: ~2 minutes.

> **Rate pacing:** `run_phase3` sleeps 4 seconds between calls (`time.sleep(4)`) to stay at ≤15 req/min. This is handled in the orchestrator loop, not inside the Gemini util (which stays stateless).

---

### `modules/phase3_outreach.py`

#### `build_outreach_prompt(lead: dict, intel: dict) -> str`

Constructs the Gemini prompt. Two pre-processing steps before the prompt is assembled:

1. **Tech signal filter** — `company_technologies` can have 80+ entries. Cross-reference against `intel.ideal_customer_profile.tech_stack_signals` to extract only Cresta-relevant tools (Five9, Genesys, NICE, Salesforce, Amazon Connect, etc.). If none match, omit the tech line entirely.
2. **Industry pain point mapping** — Map `company_industry` to 2–3 of the most relevant entries in `intel.ideal_customer_profile.pain_points`.

Prompt structure:

```
You are writing sales outreach for Cresta — an enterprise AI platform for contact centers.

CRESTA:
  Value prop: {intel.market_positioning.value_proposition}
  Differentiators: {top 3 from intel.market_positioning.differentiators}
  Relevant pain points for {industry}: {2–3 mapped pain points}

PROSPECT:
  Name: {first_name} {last_name}, {title}
  Company: {company_name} | {industry} | {employees} employees | ${revenue}
  Tech signals: {filtered tech list — omit if empty}
  Business context: {first 5 tokens from company_keywords split on ","}

Write three outreach pieces. Be specific — reference their tech stack and industry directly. Be concise and conversational.

[EMAIL_SUBJECT]
Max 8 words. No spam trigger words.
[EMAIL_BODY]
4–5 sentences: hook on their specific context → pain point → Cresta solution → soft CTA.
[CALL_SCRIPT]
Format: Opener | Discovery Q1 | Discovery Q2 | 30-second pitch
[LINKEDIN]
2–3 sentences: personalized connection request or InMail.
[END]
```

#### `parse_outreach_response(text: str) -> dict`

Splits on delimiters `[EMAIL_SUBJECT]`, `[EMAIL_BODY]`, `[CALL_SCRIPT]`, `[LINKEDIN]`, `[END]`. Returns:

```python
{
    "email_subject": str,
    "email_body": str,
    "call_script": str,
    "linkedin_message": str,
}
```

On parse failure (missing delimiter), returns empty strings for all fields and stores the full raw text in `"raw_response"`.

#### `generate_outreach(gemini, lead: dict, intel: dict) -> dict`

Calls `build_outreach_prompt` → `generate` → `parse_outreach_response`. Returns the parsed dict merged with the lead's identity fields.

#### `save_outreach(company_name: str, results: list[dict]) -> str`

Saves to `data/{company_slug}/outreach.json`:

```json
{
  "_meta": { "company": "Cresta", "generated_at": "...", "total": 30 },
  "outreach": [ { ...lead fields, ...generated fields } ]
}
```

---

## Modified Files

### `config.py`

Add: `GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")`

### `utils/sheets.py`

Add `write_outreach(client, spreadsheet_id, company_name, results)`.

**Tab name:** `"{Company Name} — Outreach"`

**Column order:**
```
Company | Industry | First Name | Last Name | Title | Email | LinkedIn URL |
Stars | Email Subject | Email Body | Call Script | LinkedIn Message
```

Rows sorted by `Stars` descending before writing.

### `orchestrator.py`

Add `run_phase3(company, state, resume)` following the same pattern as `run_phase2`:
- Skip if `resume` and `"phase3"` already in `completed_phases`
- Load leads and intel, init Gemini client
- Call `generate_outreach` per lead with a progress print
- Call `save_outreach`, then `write_outreach`
- Mark `"phase3"` complete in state, fire Discord notification to `DISCORD_WEBHOOK_UPDATES`

Add Phase 3 block in `main()` after Phase 2 block.

---

## Error Handling

| Failure | Behaviour |
|---|---|
| Gemini API error (rate limit, timeout) | Log warning, store `{"error": "...", "raw_response": ""}` for that lead, continue |
| Parse failure (missing delimiter) | Store full raw text in `raw_response`, empty strings for structured fields |
| No leads loaded | Print error, return `None` from `run_phase3` |
| No intel loaded | Print error, return `None` from `run_phase3` |

---

## Tests

### `tests/test_gemini.py` (2 tests)
- `get_client` configures the Gemini SDK with the provided API key
- `generate` calls `generate_content` on the model and returns the `.text` string

### `tests/test_phase3.py` (6 tests)
- `build_outreach_prompt` includes lead name, title, and company
- `build_outreach_prompt` includes filtered tech signals when present
- `build_outreach_prompt` omits tech line when no signals match
- `parse_outreach_response` extracts all four fields from a valid response
- `parse_outreach_response` returns empty strings on malformed input
- `generate_outreach` returns a dict with all required keys

### `tests/test_sheets.py` (append 3 tests)
- `write_outreach` creates the `"{Company} — Outreach"` tab
- `write_outreach` writes the correct column headers
- `write_outreach` writes one row per lead in Stars-descending order

---

## Acceptance Criteria

1. `python orchestrator.py --company Cresta --phase 3` completes without error
2. `data/cresta/outreach.json` exists with 30 entries, each containing all four generated fields
3. `"Cresta — Outreach"` tab exists in Google Sheets with correct columns and 30 rows
4. Discord notification fires on completion
5. All tests pass (target: ~77 total)
