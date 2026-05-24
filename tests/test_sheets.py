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


def test_read_company_list_default_active_when_status_active():
    records = [{"Company Name": "Cresta", "Website": "https://cresta.com",
                "Status": "Active", "Last Run Date": "", "Total Runs": 0, "Notes": ""}]
    mock_client, _ = _mock_client(records)
    from utils.sheets import read_company_list
    result = read_company_list(mock_client, "fake_id")
    assert len(result) == 1


import gspread


def _mock_spreadsheet_with_missing_sheet(mock_sheet):
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_sheet
    mock_spreadsheet.fetch_sheet_metadata.return_value = {"sheets": [
        {"properties": {"title": "Cresta — Pipeline", "sheetId": 1}},
        {"properties": {"title": "Cresta — Leads", "sheetId": 2}},
        {"properties": {"title": "Cresta — Intelligence", "sheetId": 3}},
        {"properties": {"title": "Cresta — Dashboard", "sheetId": 4}},
    ]}
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
    assert any("Stars" in h for h in first_call_args)
    assert any("Email" in h for h in first_call_args)


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


def _sample_outreach(stars=4):
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "title": "VP of CX",
        "email": "jane@acme.com",
        "personal_phone": "",
        "linkedin_url": "https://linkedin.com/in/janedoe",
        "company_name": "Acme Corp",
        "company_industry": "Telecommunications",
        "company_website": "https://acme.com",
        "company_phone": "+1 408-555-0000",
        "company_employees": 500,
        "company_revenue": "100M",
        "company_total_funding_clean": "50M",
        "company_age": "15",
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
    assert "Stars" in headers[0]
    assert any("Stage" in h for h in headers)
    assert any("Notes" in h for h in headers)
    assert any("Subject" in h for h in headers)
    assert any("LinkedIn Message" in h for h in headers)
    assert any("Phone" in h for h in headers)
    assert any("Website" in h for h in headers)
    assert any("Revenue" in h for h in headers)
    assert any("Funding" in h for h in headers)
    assert any("Age" in h for h in headers)
    assert any("Employees" in h for h in headers)


def test_write_outreach_sorts_rows_by_stars_descending():
    mock_sheet = MagicMock()
    mock_client, mock_spreadsheet, _ = _mock_spreadsheet_with_missing_sheet(mock_sheet)
    from utils.sheets import write_outreach
    leads = [_sample_outreach(stars=3), _sample_outreach(stars=5), _sample_outreach(stars=4)]
    write_outreach(mock_client, "fake_id", "Cresta", leads)
    rows = mock_sheet.append_rows.call_args[0][0]
    # Stars is column index 0
    assert rows[0][0] == 5
    assert rows[1][0] == 4
    assert rows[2][0] == 3
