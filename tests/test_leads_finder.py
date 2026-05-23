import pytest
from unittest.mock import patch, MagicMock


def _make_mock_client(items=None):
    """Build a mock ApifyClient that returns the given items from the dataset."""
    if items is None:
        items = []

    mock_dataset = MagicMock()
    mock_dataset.iterate_items.return_value = iter(items)

    mock_run = MagicMock()
    mock_run.default_dataset_id = "fake-dataset-id"

    mock_actor = MagicMock()
    mock_actor.call.return_value = mock_run

    mock_client = MagicMock()
    mock_client.actor.return_value = mock_actor
    mock_client.dataset.return_value = mock_dataset

    return mock_client


SAMPLE_ITEMS = [
    {
        "firstName": "Jane",
        "lastName": "Doe",
        "fullName": "Jane Doe",
        "title": "VP of Sales",
        "email": "jane.doe@acme.com",
        "linkedinUrl": "https://linkedin.com/in/janedoe",
        "companyName": "Acme Corp",
        "companyDomain": "acme.com",
        "companyIndustry": "Telecommunications",
        "companySize": "201-500",
    }
]


def test_search_leads_calls_correct_actor():
    """Verifies actor ID 'code_crafter/leads-finder' is used."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    search_leads(mock_client, job_titles=["VP of Sales"])
    mock_client.actor.assert_called_once_with("code_crafter/leads-finder")


def test_search_leads_passes_job_titles():
    """Verifies job_titles appear in run_input."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    titles = ["VP of Sales", "Head of Revenue"]
    search_leads(mock_client, job_titles=titles)
    call_kwargs = mock_client.actor.return_value.call.call_args[1]
    run_input = call_kwargs["run_input"]
    assert run_input["job_titles"] == titles


def test_search_leads_passes_company_sizes():
    """Verifies company_sizes appear in run_input when provided."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    sizes = ["201-500", "501-1000"]
    search_leads(mock_client, job_titles=["CEO"], company_sizes=sizes)
    call_kwargs = mock_client.actor.return_value.call.call_args[1]
    run_input = call_kwargs["run_input"]
    assert run_input["company_sizes"] == sizes


def test_search_leads_returns_list():
    """Verifies return type is list."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    result = search_leads(mock_client, job_titles=["Director of Engineering"])
    assert isinstance(result, list)


def test_extract_people_returns_normalized_list():
    """Verifies all required schema keys are present and values are correct."""
    from utils.leads_finder import extract_people
    people = extract_people(SAMPLE_ITEMS)
    assert len(people) == 1
    p = people[0]
    assert p["first_name"] == "Jane"
    assert p["last_name"] == "Doe"
    assert p["name"] == "Jane Doe"
    assert p["title"] == "VP of Sales"
    assert p["email"] == "jane.doe@acme.com"
    assert p["email_status"] == "unverified"
    assert p["linkedin_url"] == "https://linkedin.com/in/janedoe"
    assert p["company_name"] == "Acme Corp"
    assert p["company_website"] == "acme.com"
    assert p["company_industry"] == "Telecommunications"
    assert p["company_employees"] == "201-500"
    assert p["source"] == "leads_finder"


def test_extract_people_returns_empty_for_empty_input():
    """Verifies empty input returns empty list."""
    from utils.leads_finder import extract_people
    result = extract_people([])
    assert result == []
