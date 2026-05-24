import json
import gspread
import config
from modules.phase1_intel import load_intel
from utils.sheets import get_client, write_outreach, write_dashboard, write_company_intel

COMPANY = "Cresta"

with open(f"data/{COMPANY.lower()}/outreach.json", encoding="utf-8") as f:
    data = json.load(f)
results = data["outreach"]

# Enrich with fields not yet in outreach.json (personal_phone, company_phone, funding, age)
DATASET_PATH = r".remember\apify\dataset_leads-finder_2026-05-23_08-02-31-772.json"
with open(DATASET_PATH, encoding="utf-8") as f:
    ds_lookup = {item["email"]: item for item in json.load(f) if item.get("email")}

for r in results:
    ds = ds_lookup.get(r.get("email", ""), {})
    r.setdefault("personal_phone", ds.get("mobile_number") or "")
    r.setdefault("company_phone", ds.get("company_phone", ""))
    r.setdefault("company_total_funding_clean", ds.get("company_total_funding_clean") or "")
    founded = ds.get("company_founded_year")
    r.setdefault("company_age", str(2026 - int(founded)) if founded else "")

sheets = get_client(config.GOOGLE_CREDENTIALS_PATH)
spreadsheet = sheets.open_by_key(config.SPREADSHEET_ID)

write_outreach(sheets, config.SPREADSHEET_ID, COMPANY, results)
print(f"Pipeline written ({len(results)} rows)")

write_dashboard(sheets, config.SPREADSHEET_ID, COMPANY)
print("Dashboard written")

intel = load_intel(COMPANY)
if intel:
    write_company_intel(sheets, config.SPREADSHEET_ID, COMPANY, intel)
    print("Intelligence redesigned")
else:
    print("WARNING: No intel file found — skipping Intelligence tab")

for old_name in [f"{COMPANY} — Outreach", f"{COMPANY} — Leads"]:
    try:
        ws = spreadsheet.worksheet(old_name)
        spreadsheet.del_worksheet(ws)
        print(f"Deleted: {old_name}")
    except gspread.WorksheetNotFound:
        print(f"Already gone: {old_name}")
