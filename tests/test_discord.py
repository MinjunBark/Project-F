import pytest
from unittest.mock import patch, MagicMock


def _mock_post(status_code=204):
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def test_phase_complete_sends_embed():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_complete
        phase_complete("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Intel built")
        payload = mock_post.call_args[1]["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1


def test_phase_complete_message_contains_company():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_complete
        phase_complete("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Intel built")
        payload = mock_post.call_args[1]["json"]
        assert "Cresta" in payload["embeds"][0]["description"]


def test_phase_error_message_contains_error():
    with patch("utils.discord.requests.post", return_value=_mock_post()) as mock_post:
        from utils.discord import phase_error
        phase_error("https://discord.com/api/webhooks/fake", "phase1", "Cresta", "Timeout error")
        payload = mock_post.call_args[1]["json"]
        assert "Timeout error" in payload["embeds"][0]["description"]
        assert "failed" in payload["embeds"][0]["description"].lower()


def test_color_for_known_phases():
    from utils.discord import _color_for_phase
    assert _color_for_phase("phase1") == 0x1abc9c
    assert _color_for_phase("phase2") == 0x9b59b6
    assert _color_for_phase("error") == 0xff0000


def test_color_for_unknown_phase_returns_default():
    from utils.discord import _color_for_phase
    assert _color_for_phase("unknown") == 0x95a5a6
