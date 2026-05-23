from unittest.mock import patch, MagicMock


def test_get_client_configures_api_key():
    with patch("utils.gemini.genai") as mock_genai:
        from utils import gemini
        gemini.get_client("test-key-123")
        mock_genai.configure.assert_called_once_with(api_key="test-key-123")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")


def test_generate_returns_text():
    mock_client = MagicMock()
    mock_client.generate_content.return_value.text = "hello world"
    from utils.gemini import generate
    result = generate(mock_client, "test prompt")
    assert result == "hello world"
    mock_client.generate_content.assert_called_once_with("test prompt")
