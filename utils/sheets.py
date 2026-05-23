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
