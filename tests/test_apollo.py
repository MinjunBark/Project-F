import pytest
from unittest.mock import patch, MagicMock


def _mock_post(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


SAMPLE_APOLLO_RESPONSE = {
    "people": [
        {
            "id": "abc123",
            "first_name": "Jane",
            "last_name": "Doe",
            "name": "Jane Doe",
            "title": "VP of Customer Experience",
            "email": "jane.doe@acme.com",
            "email_status": "verified",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "organization": {
                "name": "Acme Corp",
                "website_url": "https://acme.com",
                "industry": "Telecommunications",
                "estimated_num_employees": 5000,
            },
        }
    ],
    "pagination": {"total_entries": 1, "per_page": 25, "page": 1},
}


def test_search_people_posts_to_correct_url():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)) as mock_post:
        from utils.apollo import search_people
        search_people("fake_key", titles=["VP of CX"], employee_ranges=["100,1000"])
        assert "apollo.io" in mock_post.call_args[0][0]


def test_search_people_includes_api_key_in_header():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)) as mock_post:
        from utils.apollo import search_people
        search_people("my_key", titles=["VP of CX"], employee_ranges=["501,1000"])
        headers = mock_post.call_args[1]["headers"]
        assert headers["X-Api-Key"] == "my_key"


def test_search_people_returns_response_dict():
    with patch("utils.apollo.requests.post", return_value=_mock_post(SAMPLE_APOLLO_RESPONSE)):
        from utils.apollo import search_people
        result = search_people("key", titles=["VP of CX"], employee_ranges=["100,1000"])
        assert "people" in result


def test_extract_people_returns_normalized_list():
    from utils.apollo import extract_people
    people = extract_people(SAMPLE_APOLLO_RESPONSE)
    assert len(people) == 1
    p = people[0]
    assert p["first_name"] == "Jane"
    assert p["title"] == "VP of Customer Experience"
    assert p["company_name"] == "Acme Corp"
    assert p["company_employees"] == 5000


def test_extract_people_handles_missing_organization():
    from utils.apollo import extract_people
    response = {"people": [{"id": "x", "first_name": "Bob", "last_name": "Smith",
                             "name": "Bob Smith", "title": "Director", "email": "",
                             "email_status": "", "linkedin_url": ""}]}
    people = extract_people(response)
    assert len(people) == 1
    assert people[0]["company_name"] == ""
    assert people[0]["company_employees"] is None


def test_extract_people_returns_empty_for_empty_response():
    from utils.apollo import extract_people
    people = extract_people({"people": []})
    assert people == []
