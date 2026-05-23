# Project F — Lead Generation System Design Spec
**Date:** 2026-05-22
**Status:** Approved
**Author:** Alex + Claude Code

---

## 1. Project Overview

Project F is a modular, AI-powered lead generation pipeline that serves client companies (starting with Cresta). For each client company, the system researches the company's profile, finds high-quality prospect companies that would buy from them, scores and filters those prospects, and generates tailored cold outreach templates for the Sales and Marketing teams.

**Primary consumers:**
- **Sales team** — receives phone numbers + call scripts for cold outreach
- **Marketing team** — receives verified emails + email templates for campaigns and ad targeting

**Guiding principles:**
- Phase by phase execution — complete and validate each phase before proceeding
- Quality over quantity — 15–30 high-quality leads per run
- Cost-conscious — maximize free tiers, minimize redundant API calls
- Human in the loop — team feedback drives continuous improvement
- 95% confidence before executing any phase
- Always discuss before executing new phases or changes

---

## 2. Architecture — Option B: Modular Agent Pipeline

Each phase is a self-contained Python module with a clear input → output contract. A central orchestrator coordinates execution, saves state after each phase, and sends Discord notifications.

### Execution Model
- **Trigger:** On-demand, manually by user: `python orchestrator.py --company Cresta`
- **Resumable:** If a phase fails, re-run with `--resume` to skip completed phases
- **Scale:** 15–30 leads per run (hard-capped in script)
- **Environment:** Local machine now → cloud hosted later (see Section 9)

### Folder Structure
```
/Project-F
  /data
    /cresta
      state.json              ← phase progress + resume point
      company_intel.json      ← Phase 1 output
      raw_leads.json          ← Phase 2 output
      scored_leads.json       ← Phase 3 output
      outreach.json           ← Phase 4 output
  /docs
    /superpowers/specs/       ← design specs
    /diagrams/                ← architecture diagrams
  /feedback
    /cresta/                  ← feedback reports per run
  /modules
    phase1_intel.py
    phase2_prospecting.py
    phase3_scoring.py
    phase4_outreach.py
    phase5_feedback.py
  /outreach
    /cresta/                  ← [company-name].md per lead
  /utils
    sheets.py                 ← Google Sheets read/write
    discord.py                ← Discord webhook notifications
    apollo.py                 ← Apollo API wrapper
    apify.py                  ← Apify scraping wrapper
    hunter.py                 ← Hunter.io email verification
  orchestrator.py
  config.py                   ← settings, model configs
  .env                        ← API keys (never committed to git)
  requirements.txt
```

---

## 3. Tool Stack

| Purpose | Tool | Plan | Cost |
|---|---|---|---|
| Lead database + contact finding | Apollo.io API (official) | Free → Basic | $0 → $59/mo |
| Web scraping | Apify | Free tier | $0–$29/mo |
| Email verification | Hunter.io | Free tier | $0 → $49/mo |
| AI — manual phase | Claude Code (interactive) | Existing subscription | $0 additional |
| AI — automated phase (future) | Gemini API | Free tier | $0 |
| Data (user-facing) | Google Sheets | Free | $0 |
| Data (backend) | Local JSON files | n/a | $0 |
| Communication | Discord | Free | $0 |
| Documentation | Notion | Free | $0 |
| Future automation | n8n | Self-hosted or cloud | TBD |

**Important:** Apollo scraping violates their ToS. Use official API only.

---

## 4. AI Strategy — Manual Phase vs Automated Phase

### Manual Phase (Current)
Claude Code handles all AI reasoning interactively. Python scripts handle data collection and I/O only. Zero additional API costs.

| Phase | AI Task | Who Does It |
|---|---|---|
| Phase 1 — Intel | Research + structure company profile | Claude Code (interactive) |
| Phase 2 — Prospecting | None — Apollo + Apify handle this | n/a |
| Phase 3 — Scoring | Score and reason about each lead | Claude Code (interactive) |
| Phase 4 — Outreach | Generate email + call templates | Claude Code (interactive) |
| Phase 5 — Feedback | Analyze patterns, suggest improvements | Claude Code (interactive) |

### Automated Phase (Future — Cloud Migration)
When migrating to cloud hosting + n8n scheduling, replace Claude Code interactions with Gemini API calls inside each module.

| Phase | Replace With | Gemini Model |
|---|---|---|
| Phase 1 — Intel | `gemini_client.generate()` | gemini-2.5-pro (deep research) |
| Phase 3 — Scoring | `gemini_client.generate()` | gemini-2.0-flash |
| Phase 4 — Outreach | `gemini_client.generate()` | gemini-2.0-flash |
| Phase 5 — Feedback | `gemini_client.generate()` | gemini-2.0-flash |

**Gemini Free Tier Limits:** 2.0 Flash — 15 req/min, 1,500 req/day | 2.5 Pro — 5 req/min, 25 req/day. Sufficient for 15–30 lead batches.

---

## 5. Phase 1 — Company Intelligence

### Purpose
Build a comprehensive profile of the client company (e.g., Cresta) that drives all downstream phases. If Phase 1 is wrong, everything else finds the wrong leads.

### Trigger
User selects company from Sheet 1: `python orchestrator.py --company Cresta`

### Intel Schema

**Company Profile:** Name, website, HQ, founded, funding stage, employee count, revenue estimate

**Products & Services:** Core product, key features, use cases, pricing model

**Market Positioning:** Value proposition, market segment, differentiators, current market trends

**Ideal Customer Profile (ICP) — Most Critical:**
- Target industries (e.g., financial services, healthcare, retail, telecom)
- Company size range (employees + revenue)
- Agent/call center size range
- Decision maker titles (VP CX, Dir. Contact Center Ops, CTO)
- Tech stack signals (Genesys, Five9, Avaya, Salesforce, Zendesk)
- Pain points Cresta solves (high AHT, low CSAT, agent ramp time, manual QA)
- Trigger events (digital transformation, agent scaling, CSAT drops, leadership change)
- Qualification criteria: budget indicators, authority signals, timeline triggers

**Competitor Analysis:** Direct competitors, differentiators vs each, where Cresta wins/loses

**Warm Lead Signals:** Prior engagement indicators, disqualifiers

**Content Intelligence:** Key themes, case study verticals, proven metrics (e.g., "30% AHT reduction")

### Sources Scraped (via Apify)
- Cresta.com full site (products, use cases, case studies)
- Cresta blog / articles
- G2 / Gartner reviews
- Crunchbase (funding, employee count)
- LinkedIn company page
- News / press releases
- Job postings (tech stack + hiring signals)
- Competitor comparison pages

### Output
`data/cresta/company_intel.json` + written to Sheet 2 (Company Intelligence tab)

---

## 6. Phase 2 — Prospecting

### Purpose
Find 15–30 high-quality prospect companies using Apollo API filters derived from the Phase 1 ICP, then enrich each with deeper context via Apify scraping.

### Apollo API — Lead Finding
ICP fields from Phase 1 map directly to Apollo API parameters:

| ICP Field | Apollo Parameter |
|---|---|
| Target industries | `organization_industry_tag_ids[]` |
| Decision maker titles | `person_titles[]` |
| Company size range | `organization_num_employees_ranges[]` |
| Keywords (contact center) | `q_organization_keyword_tags[]` |
| Tech stack signals | `q_keywords` |
| Verified emails only | `contact_email_status[]: verified` |
| Geography (optional) | `organization_locations[]` |

Result hard-capped at 30. Apollo returns ranked results — top matches only.

### Apify — Per-Company Enrichment
For each Apollo result, Apify scrapes:

| Source | Extracted Data |
|---|---|
| Company website | Services, contact center mentions, case studies |
| Job postings | Tech stack in use, agent count signals, hiring urgency |
| Google News | Trigger events (funding, expansion, leadership changes) |
| LinkedIn company page | Employee count, growth signals, recent posts |

Actors used: `apify/website-content-crawler`, `compass/crawler-google-places`, custom job posting actor

### Hunter.io — Email Verification
Every email from Apollo verified before saving:
- `deliverable` → keep, mark ✓
- `risky` → keep, flag ⚠️
- `undeliverable` → discard, attempt alternative ✗

### Output
`data/cresta/raw_leads.json` — 15–30 enriched lead records

---

## 7. Phase 3 — Scoring & Filtering

### Purpose
Score each lead against a weighted rubric, flag hard disqualifiers, assign 1–5 star rating with written reasoning, and filter which leads proceed to outreach.

### Hard Disqualifiers — Auto-Reject
- No telephone / contact center system
- Fewer than 50 agents
- Revenue under $10M estimated
- Wrong industry (manufacturing, agriculture, etc.)
- No verified email AND no phone number
- Company is a Cresta competitor

### Weighted Scoring Rubric

| Dimension | Weight | What Is Evaluated |
|---|---|---|
| ICP Fit | 40% | Industry match, company size, agent count, tech stack signals |
| Decision Maker Quality | 30% | Correct title, verified email, direct phone, LinkedIn accessible |
| Buying Signals | 20% | Trigger events, active contact center investment, visible pain points |
| Data Completeness | 10% | All key fields populated |

### Star Rating Scale

| Score | Stars | Status | Action |
|---|---|---|---|
| 85–100 | ⭐⭐⭐⭐⭐ | Pending | Priority outreach |
| 70–84 | ⭐⭐⭐⭐ | Pending | Standard outreach |
| 55–69 | ⭐⭐⭐ | Pending | Lower priority |
| 40–54 | ⭐⭐ | Pending | Hold |
| 25–39 | ⭐ | Pending | Low confidence |
| 0–24 | — | Reject | Logged, skipped |

Only leads **3 stars and above** proceed to Phase 4.

### Output
`data/cresta/scored_leads.json` + written to Sheet 3 (Lead Gen Results)

---

## 8. Phase 4 — Outreach Template Generation

### Purpose
Generate a personalized cold email and cold call script for each qualified lead (3+ stars), tailored using their specific pain points, trigger events, tech stack, and decision maker context combined with Cresta's proven results and value proposition.

### Cold Email Structure
- 3 subject line variants (direct, signal-based, results-based)
- Hook tied to specific trigger event
- Pain point bridge (tied to their tech stack)
- Value statement (Cresta's specific benefit)
- Social proof (industry-matched case study metric)
- Low-friction CTA (15-minute call)

### Cold Call Script Structure
- Opening with permission ask (pattern interrupt)
- Hook tied to trigger event
- 3 qualifying questions (AHT, current QA process, agent scaling)
- Value pivot based on answers
- Industry-matched proof point
- Objection handlers (3 common objections)
- CTA (15-minute demo)

### Output
- `data/cresta/outreach.json` — structured templates per lead
- `/outreach/cresta/[company-name].md` — readable markdown per lead (for sales reps)
- Sheet 3 updated: Email Template + Call Script columns populated

---

## 9. Phase 5 — Feedback Loop

### Purpose
Capture real outcomes from Sales and Marketing after outreach, analyze patterns across runs, and continuously refine the scoring rubric and ICP for higher quality leads over time.

### How the Team Contributes — Sheet 3 Fields

**Sales fills in:**
Contacted, Contact Date, Outcome (Interested/Not Interested/No Response/Meeting Booked/Closed Won/Closed Lost), Decision Maker Accuracy, Score Accuracy, Sales Notes, Follow-up Date

**Marketing fills in:**
Email Opened, Email Replied, Ad Targeted, Campaign Response, Marketing Notes

### Feedback Processing
Run: `python orchestrator.py --feedback Cresta`

Claude Code reads Sheet 3 feedback, analyzes patterns across all runs, and generates a report in `/feedback/cresta/feedback-report-YYYY-MM-DD.md` containing:
- Which signals predicted success vs failure
- Scoring weight adjustment recommendations
- ICP refinement suggestions
- New disqualifier candidates
- Template improvement notes

All changes require human approval before being applied. Changes are version-logged.

### Improvement Cycle
Run 1 → feedback → Run 2 (smarter ICP) → feedback → Run 3 (refined scoring) → ...

---

## 10. Google Sheets Structure

### Sheet 1 — Company List (Input)
Fields: Company Name, Website, Status (Active/Paused), Last Run Date, Total Runs, Notes

### Sheet 2 — Company Intelligence (Output, one per company)
Vertical format (Field | Value). Named: `[Company] — Intelligence`
Sections: Company Profile, Products & Services, Market Positioning, ICP, Competitor Analysis, Warm Lead Signals, Content Intelligence, Meta

### Sheet 3 — Lead Gen Results (Output, one per company)
Named: `[Company] — Leads`. ~30 fields per lead row. Sorted by star rating descending.
Sections: Identity, Qualification (ICP match), Contact (Sales + Marketing), Outreach, Tracking (Human-in-Loop)

---

## 11. Discord — Project F Server

### Channel Structure
```
PROJECT F SERVER
├── #announcements       ← System run completions, major updates
├── #lead-gen-updates    ← Auto-post per phase completion
├── #cresta-leads        ← New leads posted for team review
├── #feedback            ← Team discusses lead quality
├── #scoring-decisions   ← Flagged leads needing human review
└── #system-logs         ← Errors, run summaries, troubleshooting
```

### Automated Webhook Notifications
Phase completions, new leads, feedback prompts, errors, and flagged uncertain leads all post automatically to relevant channels.

---

## 12. Migration Path

### Phase A — Current (Manual + Local)
- Python scripts run locally, triggered manually
- Claude Code handles all AI tasks interactively
- Google Sheets as data store
- Discord for communication

### Phase B — Semi-Automated (Cloud Hosted)
- Scripts hosted on cloud (Google Cloud Run or AWS Lambda)
- Replace Claude Code AI interactions with Gemini API calls
- Add scheduling capability
- Database migration from JSON to Supabase/PostgreSQL

### Phase C — Fully Automated (n8n Migration)
- n8n orchestrates the entire pipeline on schedule
- Each Python module becomes an n8n node
- Full autonomy — runs without human trigger
- Feedback loop fully integrated into scheduling

---

## 13. Setup Checklist (First-Time)

### User Setup Tasks (Requires Manual Action)
- [ ] Create Google Cloud project + enable Sheets API → get credentials JSON
- [ ] Create Google Sheets (3 sheets) + share with service account
- [ ] Create Apollo.io account → get API key
- [ ] Create Apify account → get API token
- [ ] Create Hunter.io account → get API key
- [ ] Create Discord server "Project F" + create webhook URLs per channel
- [ ] Create Notion workspace for technical documentation

### System Setup Tasks (Claude Code assists)
- [ ] Initialize Python project + `requirements.txt`
- [ ] Configure `.env` with all API keys
- [ ] Build `utils/sheets.py` Google Sheets connector
- [ ] Build `utils/discord.py` webhook notifier
- [ ] Build `utils/apollo.py` API wrapper
- [ ] Build `utils/apify.py` scraping wrapper
- [ ] Build `utils/hunter.py` email verification wrapper
- [ ] Build `orchestrator.py` with phase coordination + resume logic
- [ ] Build Phase 1 module
- [ ] Test Phase 1 end-to-end with Cresta

---

*Spec written by Claude Code | Project F | 2026-05-22*
