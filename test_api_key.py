from reviewer import get_client
import pytest


def test_get_client_requires_key_when_env_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(EnvironmentError, match="GEMINI_API_KEY not found"):
        get_client()
