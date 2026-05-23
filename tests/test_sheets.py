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
