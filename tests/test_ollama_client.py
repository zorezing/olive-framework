from unittest.mock import Mock, patch

import requests

from olive.workflow.ollama_client import OllamaClient


def test_is_available_true_on_200():
    client = OllamaClient()

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200)

        assert client.is_available() is True


def test_is_available_false_on_non_200():
    client = OllamaClient()

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=500)

        assert client.is_available() is False


def test_is_available_false_on_connection_error():
    client = OllamaClient()

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("refused")

        assert client.is_available() is False


def test_is_available_false_on_timeout():
    client = OllamaClient()

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.side_effect = requests.Timeout("timed out")

        assert client.is_available() is False


def test_is_available_uses_short_health_timeout_not_chat_timeout():
    client = OllamaClient(timeout=1800)

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200)

        client.is_available()

        _, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 3.0


def test_is_available_hits_the_tags_endpoint():
    client = OllamaClient(base_url="http://example.local:11434")

    with patch("olive.workflow.ollama_client.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200)

        client.is_available()

        args, _ = mock_get.call_args
        assert args[0] == "http://example.local:11434/api/tags"
