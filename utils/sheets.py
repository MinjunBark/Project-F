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
