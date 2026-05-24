import pytest
from unittest.mock import MagicMock


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
        "first_name": "Jane",
        "last_name": "Doe",
        "full_name": "Jane Doe",
        "job_title": "VP of Sales",
        "email": "jane.doe@acme.com, jane@acme.com",
        "mobile_number": "+1 555-111-2222",
        "linkedin": "https://linkedin.com/in/janedoe",
        "company_name": "Acme Corp",
        "company_website": "https://acme.com",
        "industry": "Telecommunications",
        "company_size": 450,
        "company_technologies": "salesforce, five9",
        "keywords": "ai, customer service",
        "company_annual_revenue_clean": "50M",
        "company_phone": "+1 555-123-4567",
        "company_total_funding_clean": "10M",
        "company_founded_year": "2010",
    }
]


def test_search_leads_calls_correct_actor():
    """Verifies actor ID 'code_crafter/leads-finder' is used."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    search_leads(mock_client, job_titles=["VP of Sales"])
    mock_client.actor.assert_called_once_with("code_crafter/leads-finder")


def test_search_leads_passes_job_titles():
    """Verifies job titles appear in run_input (param name TBD for code_crafter)."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    titles = ["VP of Sales", "Head of Revenue"]
    search_leads(mock_client, job_titles=titles)
    call_kwargs = mock_client.actor.return_value.call.call_args[1]
    run_input = call_kwargs["run_input"]
    assert run_input["personTitle"] == titles  # TODO: verify correct param name for code_crafter


def test_search_leads_passes_company_sizes():
    """Verifies company_sizes appear in run_input (param name TBD for code_crafter)."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    sizes = ["201 - 500", "501 - 1000"]
    search_leads(mock_client, job_titles=["CEO"], company_sizes=sizes)
    call_kwargs = mock_client.actor.return_value.call.call_args[1]
    run_input = call_kwargs["run_input"]
    assert run_input["companyEmployeeSize"] == sizes  # TODO: verify correct param name for code_crafter


def test_search_leads_returns_list():
    """Verifies return type is list."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    result = search_leads(mock_client, job_titles=["Director of Engineering"])
    assert isinstance(result, list)


def test_extract_people_returns_normalized_list():
    """Verifies all required schema keys are present and values are mapped correctly."""
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
    assert p["personal_phone"] == "+1 555-111-2222"
    assert p["linkedin_url"] == "https://linkedin.com/in/janedoe"
    assert p["company_name"] == "Acme Corp"
    assert p["company_website"] == "https://acme.com"
    assert p["company_industry"] == "Telecommunications"
    assert p["company_employees"] == 450
    assert p["company_phone"] == "+1 555-123-4567"
    assert p["company_revenue"] == "50M"
    assert p["company_total_funding_clean"] == "10M"
    assert p["company_age"] == "16"   # 2026 - 2010
    assert p["source"] == "leads_finder"


def test_extract_people_returns_empty_for_empty_input():
    """Verifies empty input returns empty list."""
    from utils.leads_finder import extract_people
    result = extract_people([])
    assert result == []


def test_extract_people_takes_first_email_from_comma_list():
    """Verifies comma-separated emails are split and only the first is kept."""
    from utils.leads_finder import extract_people
    item = {**SAMPLE_ITEMS[0], "email": "primary@example.com, secondary@example.com"}
    people = extract_people([item])
    assert people[0]["email"] == "primary@example.com"


def test_search_leads_passes_industry_when_provided():
    """Verifies industry string is wrapped in a list for the actor input."""
    from utils.leads_finder import search_leads
    mock_client = _make_mock_client([])
    search_leads(mock_client, job_titles=["VP"], industry="Software Development")
    run_input = mock_client.actor.return_value.call.call_args[1]["run_input"]
    assert run_input.get("industry") == ["Software Development"]
