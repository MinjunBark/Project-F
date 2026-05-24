from unittest.mock import patch, MagicMock


def test_get_client_returns_client_for_api_key():
    with patch("utils.gemini.genai") as mock_genai:
        mock_genai.Client.return_value = MagicMock()
        from utils import gemini
        client = gemini.get_client("test-key-123")
        mock_genai.Client.assert_called_once_with(api_key="test-key-123")
        assert client is mock_genai.Client.return_value


def test_generate_returns_text():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = "hello world"
    from utils.gemini import generate
    result = generate(mock_client, "test prompt")
    assert result == "hello world"
    mock_client.models.generate_content.assert_called_once_with(
        model="gemini-2.5-flash", contents="test prompt"
    )
