from reviewer import get_client
import pytest
from unittest.mock import patch


def test_get_client_requires_key_when_env_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY not found"):
        get_client()


def test_get_client_uses_environment_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "environment-key")

    with patch("reviewer.genai.Client") as client:
        get_client()

    client.assert_called_once_with(api_key="environment-key")


def test_get_client_uses_streamlit_secret(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("reviewer.st.secrets", {"GEMINI_API_KEY": "secret-key"})

    with patch("reviewer.genai.Client") as client:
        get_client()

    client.assert_called_once_with(api_key="secret-key")
