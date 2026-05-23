import pytest
from unittest.mock import patch, MagicMock


def _mock_get(json_data, status_code=200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


VERIFY_RESPONSE = {
    "data": {
        "status": "valid",
        "score": 92,
        "email": "jane.doe@acme.com",
    }
}

FIND_RESPONSE = {
    "data": {
        "email": "j.doe@acme.com",
        "confidence": 78,
    }
}

FIND_EMPTY_RESPONSE = {"data": {"email": None, "confidence": 0}}


def test_verify_email_returns_status_and_score():
    with patch("utils.hunter.requests.get", return_value=_mock_get(VERIFY_RESPONSE)):
        from utils.hunter import verify_email
        result = verify_email("fake_key", "jane.doe@acme.com")
        assert result["status"] == "valid"
        assert result["score"] == 92
        assert result["email"] == "jane.doe@acme.com"


def test_verify_email_raises_on_http_error():
    mock = _mock_get({}, status_code=401)
    mock.raise_for_status.side_effect = Exception("401 Unauthorized")
    with patch("utils.hunter.requests.get", return_value=mock):
        from utils.hunter import verify_email
        with pytest.raises(Exception):
            verify_email("bad_key", "x@y.com")


def test_find_email_returns_email_and_confidence():
    with patch("utils.hunter.requests.get", return_value=_mock_get(FIND_RESPONSE)):
        from utils.hunter import find_email
        result = find_email("fake_key", "acme.com", "Jane", "Doe")
        assert result["email"] == "j.doe@acme.com"
        assert result["confidence"] == 78


def test_find_email_returns_empty_string_if_not_found():
    with patch("utils.hunter.requests.get", return_value=_mock_get(FIND_EMPTY_RESPONSE)):
        from utils.hunter import find_email
        result = find_email("fake_key", "acme.com", "Unknown", "Person")
        assert result["email"] == ""
        assert result["confidence"] == 0


def test_verify_email_passes_api_key_in_params():
    with patch("utils.hunter.requests.get", return_value=_mock_get(VERIFY_RESPONSE)) as mock_get:
        from utils.hunter import verify_email
        verify_email("mykey", "test@test.com")
        params = mock_get.call_args[1]["params"]
        assert params["api_key"] == "mykey"
