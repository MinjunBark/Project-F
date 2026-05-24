import gspread
from datetime import date
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ── Base colors ────────────────────────────────────────────────────────────────
_NAV  = {"red": 0.10, "green": 0.10, "blue": 0.18}   # dark navy header
_WHT  = {"red": 1.00, "green": 1.00, "blue": 1.00}   # white
_ALT  = {"red": 0.94, "green": 0.96, "blue": 0.97}   # light blue-gray alt row
_GRN  = {"red": 0.20, "green": 0.66, "blue": 0.33}   # 5-star green / Won
_GLD  = {"red": 0.98, "green": 0.74, "blue": 0.02}   # 4-star gold
_AMB  = {"red": 1.00, "green": 0.60, "blue": 0.00}   # 3-star amber

# ── Stage chip colors ─────────────────────────────────────────────────────────
_CHIP_NEW  = {"red": 0.90, "green": 0.90, "blue": 0.90}   # light gray
_CHIP_CONT = {"red": 1.00, "green": 0.97, "blue": 0.82}   # light yellow
_CHIP_FWUP = {"red": 1.00, "green": 0.89, "blue": 0.73}   # light orange
_CHIP_QUAL = {"red": 0.82, "green": 0.94, "blue": 0.90}   # light teal
_CHIP_DEMO = {"red": 0.93, "green": 0.87, "blue": 0.98}   # lavender
_CHIP_PROP = {"red": 0.82, "green": 0.91, "blue": 0.98}   # light blue
_CHIP_LOST = {"red": 1.00, "green": 0.88, "blue": 0.88}   # light pink
_CHIP_NURT = {"red": 0.84, "green": 0.87, "blue": 0.91}   # blue-gray

# ── Dropdown option lists ──────────────────────────────────────────────────────
_STAGE_OPTS = [
    "🆕 New", "📤 Contacted", "🔁 Follow-Up", "✅ Qualified",
    "📅 Demo Booked", "📋 Proposal Sent", "🏆 Won", "❌ Lost", "💤 Nurture",
]
_RESPONSE_OPTS = [
    "⬜ No Response", "✅ Interested", "❌ Not Interested",
    "📅 Meeting Booked", "↩️ Bounced", "🏖️ Out of Office",
]


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
            sheet.update_cell(i, date_col, date.today().strftime("%Y-%m-%d"))
            sheet.update_cell(i, runs_col, int(record.get("Total Runs", 0)) + 1)
            return


# ── Formatting helpers ─────────────────────────────────────────────────────────

def _get_sheet_id(spreadsheet: gspread.Spreadsheet, sheet_name: str) -> int:
    for s in spreadsheet.fetch_sheet_metadata()["sheets"]:
        if s["properties"]["title"] == sheet_name:
            return s["properties"]["sheetId"]
    raise ValueError(f"Sheet '{sheet_name}' not found")


def _freeze(sid: int, rows: int = 1, cols: int = 0) -> dict:
    return {"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols}},
        "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
    }}


def _header_style(sid: int, num_cols: int) -> dict:
    return {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": num_cols}, "cell": {"userEnteredFormat": {"backgroundColor": _NAV, "textFormat": {"foregroundColor": _WHT, "bold": True, "fontSize": 11}, "verticalAlignment": "MIDDLE", "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,horizontalAlignment)"}}


def _col_width(sid: int, col: int, px: int) -> dict:
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": col, "endIndex": col + 1}, "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def _row_height(sid: int, start: int, end: int, px: int) -> dict:
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": start, "endIndex": end}, "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def _wrap(sid: int, start_row: int, end_row: int, start_col: int, end_col: int) -> dict:
    return {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": start_col, "endColumnIndex": end_col}, "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"}}, "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}}


def _clip(sid: int, start_row: int, end_row: int, start_col: int, end_col: int) -> dict:
    return {"repeatCell": {"range": {"sheetId": sid, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": start_col, "endColumnIndex": end_col}, "cell": {"userEnteredFormat": {"wrapStrategy": "CLIP", "verticalAlignment": "MIDDLE"}}, "fields": "userEnteredFormat(wrapStrategy,verticalAlignment)"}}


def _center_bold(sid: int, start_row: int, end_row: int, col: int) -> dict:
    return {"repeatCell": {
        "range": {"sheetId": sid, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": col, "endColumnIndex": col + 1},
        "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER", "textFormat": {"bold": True}}},
        "fields": "userEnteredFormat(horizontalAlignment,textFormat.bold)",
    }}


def _banding(sid: int, num_rows: int) -> dict:
    return {"addBanding": {"bandedRange": {"range": {"sheetId": sid, "startRowIndex": 1, "endRowIndex": num_rows + 1}, "rowProperties": {"firstBandColor": _WHT, "secondBandColor": _ALT}}}}


def _star_rule(sid: int, stars_col: int, num_cols: int, value: int, color: dict, idx: int) -> dict:
    return {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": num_cols}], "booleanRule": {"condition": {"type": "NUMBER_EQ", "values": [{"userEnteredValue": str(value)}]}, "format": {"backgroundColor": color}}}, "index": idx}}


def _stage_rule(sid: int, num_cols: int, value: str, color: dict, idx: int) -> dict:
    """Row-level highlight: colors the entire row when Stage column matches value."""
    return {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": num_cols}], "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=$B2="{value}"'}]}, "format": {"backgroundColor": color}}}, "index": idx}}


def _chip_rule(sid: int, col: int, value: str, color: dict, idx: int) -> dict:
    """Cell-level chip: colors only a single column cell when it matches value."""
    col_letter = chr(ord("A") + col)
    return {"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid, "startRowIndex": 1, "startColumnIndex": col, "endColumnIndex": col + 1}], "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=${col_letter}2="{value}"'}]}, "format": {"backgroundColor": color, "textFormat": {"bold": True}}}}, "index": idx}}


def _dropdown(sid: int, start_row: int, end_row: int, col: int, values: list[str]) -> dict:
    return {"setDataValidation": {
        "range": {"sheetId": sid, "startRowIndex": start_row, "endRowIndex": end_row, "startColumnIndex": col, "endColumnIndex": col + 1},
        "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in values]},
            "showCustomUi": True,
            "strict": False,
        },
    }}


def _format_pipeline_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str, num_rows: int):
    sid = _get_sheet_id(spreadsheet, sheet_name)
    nc = 25
    # Stars(0) Stage(1) First(2) Last(3) Title(4) Company(5) Industry(6) PersonalPhone(7)
    # Email(8) LinkedIn(9) CompanyPhone(10) DateAdded(11) Owner(12) LastContacted(13)
    # NextFollowup(14) Notes(15) CallScript(16) LinkedInMsg(17) Subject(18) EmailBody(19)
    # Website(20) Employees(21) Revenue(22) Funding(23) CompanyAge(24)
    widths = [60, 160, 120, 120, 190, 180, 150, 130, 230, 220, 130, 120, 130, 130, 130, 260, 480, 360, 260, 420, 200, 100, 100, 100, 80]
    requests = [
        _freeze(sid, rows=1, cols=2),
        _header_style(sid, nc),
        _row_height(sid, 0, 1, 40),
        _row_height(sid, 1, num_rows + 1, 180),
        _clip(sid, 1, num_rows + 1, 0, 16),
        _wrap(sid, 1, num_rows + 1, 16, 20),
        _clip(sid, 1, num_rows + 1, 20, 25),
        _center_bold(sid, 1, num_rows + 1, 1),   # Stage
        _banding(sid, num_rows),
        # ── Row-level highlights (highest priority) ────────────────────────────
        _stage_rule(sid, nc, "🏆 Won",  _GRN,      0),
        _stage_rule(sid, nc, "❌ Lost", _CHIP_LOST, 1),
        # ── Stage column chips (idx 2–10) ──────────────────────────────────────
        _chip_rule(sid, 1, "🆕 New",           _CHIP_NEW,  2),
        _chip_rule(sid, 1, "📤 Contacted",     _CHIP_CONT, 3),
        _chip_rule(sid, 1, "🔁 Follow-Up",     _CHIP_FWUP, 4),
        _chip_rule(sid, 1, "✅ Qualified",     _CHIP_QUAL, 5),
        _chip_rule(sid, 1, "📅 Demo Booked",   _CHIP_DEMO, 6),
        _chip_rule(sid, 1, "📋 Proposal Sent", _CHIP_PROP, 7),
        _chip_rule(sid, 1, "🏆 Won",           _GRN,       8),
        _chip_rule(sid, 1, "❌ Lost",          _CHIP_LOST, 9),
        _chip_rule(sid, 1, "💤 Nurture",       _CHIP_NURT, 10),
        # ── Dropdown ───────────────────────────────────────────────────────────
        _dropdown(sid, 1, num_rows + 1, 1, _STAGE_OPTS),
    ] + [_col_width(sid, i, w) for i, w in enumerate(widths)]
    spreadsheet.batch_update({"requests": requests})


def _format_leads_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str, num_rows: int):
    sid = _get_sheet_id(spreadsheet, sheet_name)
    nc = 16
    widths = [60, 70, 90, 110, 100, 90, 110, 180, 200, 110, 80, 180, 180, 140, 90, 80]
    requests = [
        _freeze(sid),
        _header_style(sid, nc),
        _row_height(sid, 0, 1, 40),
        _row_height(sid, 1, num_rows + 1, 55),
        _clip(sid, 1, num_rows + 1, 0, nc),
        _banding(sid, num_rows),
        _star_rule(sid, 0, nc, 5, _GRN, 0),
        _star_rule(sid, 0, nc, 4, _GLD, 1),
        _star_rule(sid, 0, nc, 3, _AMB, 2),
    ] + [_col_width(sid, i, w) for i, w in enumerate(widths)]
    spreadsheet.batch_update({"requests": requests})


def _format_intel_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str, num_rows: int):
    sid = _get_sheet_id(spreadsheet, sheet_name)
    nc = 2
    requests = [
        _freeze(sid),
        _header_style(sid, nc),
        _row_height(sid, 0, 1, 40),
        _row_height(sid, 1, num_rows + 1, 60),
        _clip(sid, 1, num_rows + 1, 0, 1),
        _wrap(sid, 1, num_rows + 1, 1, 2),
        _col_width(sid, 0, 240),
        _col_width(sid, 1, 540),
        _banding(sid, num_rows),
        # Section header rows (=== LABEL ===): dark navy + white bold — matches top header
        {"addConditionalFormatRule": {"rule": {
            "ranges": [{"sheetId": sid, "startRowIndex": 1, "endRowIndex": num_rows + 1, "startColumnIndex": 0, "endColumnIndex": 2}],
            "booleanRule": {
                "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": '=LEFT($A2,3)="==="'}]},
                "format": {"backgroundColor": _NAV, "textFormat": {"foregroundColor": _WHT, "bold": True}},
            }
        }, "index": 0}},
    ]
    spreadsheet.batch_update({"requests": requests})


def _format_dashboard_sheet(spreadsheet: gspread.Spreadsheet, sheet_name: str, num_rows: int):
    sid = _get_sheet_id(spreadsheet, sheet_name)
    extra = 25  # headroom for QUERY-expanded owner rows
    requests = [
        _freeze(sid),
        _header_style(sid, 2),
        _row_height(sid, 0, 1, 40),
        _row_height(sid, 1, num_rows + extra, 35),
        _clip(sid, 1, num_rows + extra, 0, 2),
        _banding(sid, num_rows + extra - 1),
        _col_width(sid, 0, 220),
        _col_width(sid, 1, 80),
    ]
    spreadsheet.batch_update({"requests": requests})


# ── Write functions ────────────────────────────────────────────────────────────

def write_company_intel(client: gspread.Client, spreadsheet_id: str,
                        company_name: str, intel: dict):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Intelligence"
    try:
        spreadsheet.del_worksheet(spreadsheet.worksheet(sheet_name))
    except gspread.WorksheetNotFound:
        pass
    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=150, cols=2)
    sheet.append_row(["📋 Field", "💡 Value"])
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
    _format_intel_sheet(spreadsheet, sheet_name, len(rows))


def write_leads(client: gspread.Client, spreadsheet_id: str,
                company_name: str, leads: list[dict]):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Leads"
    try:
        sheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=18)

    sheet.clear()
    sheet.append_row([
        "⭐ Stars", "📊 Score", "🎯 ICP Fit", "👔 Decision Maker",
        "📡 Buying Signals", "✅ Data", "👤 First Name", "💼 Title",
        "📧 Email", "✉️ Email Status", "🔗 LinkedIn", "🏢 Company",
        "🌐 Website", "🏭 Industry", "👥 Employees", "🏷️ Status",
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
    _format_leads_sheet(spreadsheet, sheet_name, len(rows))


def write_outreach(client: gspread.Client, spreadsheet_id: str,
                   company_name: str, results: list[dict]):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Pipeline"
    # Delete and recreate to reset all formatting (banding, CF rules, etc.)
    try:
        spreadsheet.del_worksheet(spreadsheet.worksheet(sheet_name))
    except gspread.WorksheetNotFound:
        pass
    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=200, cols=25)

    sheet.clear()
    sheet.append_row([
        "⭐ Stars", "🔄 Stage", "👤 First Name", "👤 Last Name", "💼 Title",
        "🏢 Company", "🏭 Industry", "📱 Personal Phone", "📧 Email", "🔗 LinkedIn",
        "📞 Company Phone", "📅 Date Added", "🧑‍💼 Owner",
        "📞 Last Contacted", "🗓️ Next Follow-up", "📝 Notes",
        "📞 Call Script", "💬 LinkedIn Message", "📩 Email Subject", "📝 Email Body",
        "🌐 Company Website", "👥 Employees", "💰 Revenue", "💸 Funding", "🏗️ Company Age",
    ])

    today = date.today().strftime("%Y-%m-%d")
    sorted_results = sorted(results, key=lambda r: r.get("scoring", {}).get("stars", 0), reverse=True)
    rows = [
        [
            r.get("scoring", {}).get("stars", ""),
            "🆕 New",
            r.get("first_name", ""),
            r.get("last_name", ""),
            r.get("title", ""),
            r.get("company_name", ""),
            r.get("company_industry", ""),
            r.get("personal_phone", "") or "",
            r.get("email", ""),
            r.get("linkedin_url", ""),
            r.get("company_phone", ""),
            today,
            "",
            "",
            "",
            "",
            r.get("call_script", ""),
            r.get("linkedin_message", ""),
            r.get("email_subject", ""),
            r.get("email_body", ""),
            r.get("company_website", ""),
            r.get("company_employees", ""),
            r.get("company_revenue", ""),
            r.get("company_total_funding_clean", ""),
            r.get("company_age", ""),
        ]
        for r in sorted_results
    ]
    if rows:
        sheet.append_rows(rows)
    _format_pipeline_sheet(spreadsheet, sheet_name, len(rows))


def write_dashboard(client: gspread.Client, spreadsheet_id: str, company_name: str):
    spreadsheet = client.open_by_key(spreadsheet_id)
    sheet_name = f"{company_name} — Dashboard"
    pipeline_name = f"{company_name} — Pipeline"
    try:
        spreadsheet.del_worksheet(spreadsheet.worksheet(sheet_name))
    except gspread.WorksheetNotFound:
        pass
    sheet = spreadsheet.add_worksheet(title=sheet_name, rows=30, cols=2)
    p = pipeline_name
    owner_query = (
        f"=IFERROR(QUERY('{p}'!A:Y,"
        "\"SELECT M, COUNT(A) WHERE M<>'' GROUP BY M ORDER BY COUNT(A) DESC "
        "LABEL M 'Owner', COUNT(A) 'Leads'\",0),\"No owners yet\")"
    )
    rows = [
        [f"📊 Pipeline Summary — {company_name}", ""],
        ["Stage", "Count"],
        ["🆕 New",           f"=COUNTIF('{p}'!B:B,\"🆕 New\")"],
        ["📤 Contacted",     f"=COUNTIF('{p}'!B:B,\"📤 Contacted\")"],
        ["🔁 Follow-Up",     f"=COUNTIF('{p}'!B:B,\"🔁 Follow-Up\")"],
        ["✅ Qualified",     f"=COUNTIF('{p}'!B:B,\"✅ Qualified\")"],
        ["📅 Demo Booked",   f"=COUNTIF('{p}'!B:B,\"📅 Demo Booked\")"],
        ["📋 Proposal Sent", f"=COUNTIF('{p}'!B:B,\"📋 Proposal Sent\")"],
        ["🏆 Won",           f"=COUNTIF('{p}'!B:B,\"🏆 Won\")"],
        ["❌ Lost",          f"=COUNTIF('{p}'!B:B,\"❌ Lost\")"],
        ["💤 Nurture",       f"=COUNTIF('{p}'!B:B,\"💤 Nurture\")"],
        ["Total",            "=SUM(B3:B11)"],
        ["", ""],
        ["🏆 Win Rate",      "=IF(B9+B10=0,\"N/A\",TEXT(B9/(B9+B10),\"0%\"))"],
        ["📤 Contacted Rate","=IF(B12=0,\"N/A\",TEXT((B12-B3)/B12,\"0%\"))"],
        ["", ""],
        [f"👥 By Owner — {company_name}", ""],
        [owner_query, ""],   # auto-expands: Owner | Leads per row
    ]
    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    _format_dashboard_sheet(spreadsheet, sheet_name, len(rows))
