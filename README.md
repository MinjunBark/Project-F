# Project F - B2B Lead Generation Pipeline

A modular Python pipeline that automates B2B lead prospecting, scoring, and personalized outreach generation. Configured per client company; outputs a fully formatted CRM in Google Sheets with Discord notifications.

---

## What it does

Given a target client company (e.g. an AI software vendor), the pipeline:

1. **Scrapes** the client's website and recent news to build a company intelligence profile
2. **Finds** ICP-matched decision-maker leads via LinkedIn data (Apify)
3. **Scores** each lead (ICP fit, title seniority, buying signals, data completeness) on a 100-point scale
4. **Verifies** email addresses via Hunter.io
5. **Generates** personalized outreach -- email, call script, LinkedIn message -- via Gemini 2.5 Flash
6. **Writes** everything to a Google Sheet: Pipeline CRM, Lead Scoring, Intelligence, and Dashboard tabs
7. **Notifies** a Discord server on phase completion or errors

---

## Architecture

```
orchestrator.py
      |
      +-- Phase 1: Company Intelligence
      |     modules/phase1_intel.py
      |     utils/apify.py       (scrape website + Google News)
      |     [manual step] Claude Code analysis -> company_intel.json
      |
      +-- Phase 2: Prospecting
      |     modules/phase2_prospecting.py
      |     utils/leads_finder.py  (Apify leads-finder actor)
      |     utils/hunter.py        (email verify / find)
      |
      +-- Phase 3: Outreach Generation
      |     modules/phase3_outreach.py
      |     utils/gemini.py        (Gemini 2.5 Flash, dual-key parallel)
      |
      +-- Sheets + Notifications (all phases)
            utils/sheets.py        (gspread: Pipeline, Leads, Intel, Dashboard)
            utils/discord.py       (phase notifications + error alerts)
```

---

## Key components

| File | Role |
|------|------|
| `orchestrator.py` | Main entry point; drives phases 1-3, manages state, supports resume |
| `config.py` | Loads all secrets from `.env` via python-dotenv |
| `modules/phase1_intel.py` | Scraping task builder, Claude prompt prep, intel save/load |
| `modules/phase2_prospecting.py` | Lead scoring (100-pt), dedup, ICP filtering |
| `modules/phase3_outreach.py` | Gemini outreach generator (email / call script / LinkedIn) |
| `utils/apify.py` | Apify client wrapper (website crawl, Google search scrape) |
| `utils/leads_finder.py` | Apify `code_crafter/leads-finder` actor integration |
| `utils/hunter.py` | Hunter.io email verify and find-by-domain |
| `utils/gemini.py` | Gemini API client with exponential backoff and multi-key fallback |
| `utils/sheets.py` | Google Sheets CRM writer with formatting, dropdowns, and dashboards |
| `utils/discord.py` | Discord embed notifications per phase |
| `apply_pipeline.py` | Loads outreach.json and writes results to Sheets (no re-generation) |
| `import_leads.py` | Imports leads from a local JSON file, enriches, and writes to Sheets |

---

## Folder structure

```
Project F/
+-- modules/               Phase business logic
+-- utils/                 External API clients and helpers
+-- tests/                 Pytest unit tests (74+ tests, 9 test files)
+-- docs/                  Architecture diagrams and design specs
+-- data/                  Runtime output -- gitignored
|   +-- <company>/
|       +-- state.json           Pipeline state (completed phases)
|       +-- phase1_raw.json      Raw scraped content
|       +-- phase1_prompt.txt    Claude analysis prompt
|       +-- company_intel.json   Structured intelligence (Phase 1 output)
|       +-- raw_leads.json       Scored and filtered leads (Phase 2 output)
|       +-- seen_leads.json      Deduplication tracker
|       +-- outreach.json        Personalized messages (Phase 3 output)
+-- orchestrator.py
+-- apply_pipeline.py
+-- import_leads.py
+-- config.py
+-- requirements.txt
+-- .env.example
```

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd project-f
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in each value:

| Variable | Description |
|----------|-------------|
| `GOOGLE_CREDENTIALS_PATH` | Path to your Google service account JSON file |
| `SPREADSHEET_ID` | ID from your Google Sheet URL |
| `APIFY_TOKEN` | Apify API token (Settings -> Integrations at apify.com) |
| `HUNTER_API_KEY` | Hunter.io API key |
| `GEMINI_API_KEY` | Google Gemini API key (primary) |
| `GEMINI_API_KEY_2` | Google Gemini API key (fallback for parallel batches) |
| `DISCORD_WEBHOOK_UPDATES` | Webhook URL for #lead-gen-updates channel |
| `DISCORD_WEBHOOK_LEADS` | Webhook URL for #cresta-leads channel |
| `DISCORD_WEBHOOK_LOGS` | Webhook URL for #system-logs channel |
| `MAX_LEADS_PER_RUN` | Max leads to process per run (default: 30) |
| `MIN_STAR_RATING_FOR_OUTREACH` | Min lead quality to generate outreach for (default: 3, max: 5) |

### 3. Google Sheets setup

1. Create a Google Cloud project and enable the Sheets API
2. Create a service account and download the credentials JSON
3. Share your target spreadsheet with the service account email
4. Add a **Company List** sheet with columns: `Company Name`, `Website`, `Status`, `Last Run Date`, `Total Runs`

---

## Running the pipeline

```bash
# Full run (phases 1 -> 3)
python orchestrator.py --company "Acme Corp"

# Resume from Phase 2 after completing the Phase 1 manual step
python orchestrator.py --company "Acme Corp" --resume

# Run a specific phase only
python orchestrator.py --company "Acme Corp" --phase 2

# Write existing outreach.json to Sheets (no re-generation)
python apply_pipeline.py --company "Acme Corp"

# Import leads from a local JSON file
python import_leads.py --company "Acme Corp" --file path/to/leads.json
```

**Phase 1 note:** Phase 1 scrapes raw data and pauses. It prints the path to a prompt file. Paste that prompt into Claude Code, save the JSON response to `data/<company>/company_intel.json`, then re-run with `--resume` to continue from Phase 2.

---

## Running tests

```bash
pytest tests/
```

---

## Adding a new client company

1. Add a row to the **Company List** sheet with `Status = Active`
2. Run `python orchestrator.py --company "<Company Name>"`
