"""Shared test setup."""
import pytest


@pytest.fixture(autouse=True)
def no_real_api_key(monkeypatch):
    """Tests must never call the real Claude API, even when a local .env holds a key.

    An empty variable wins over .env (python-dotenv does not override existing variables), so the app
    behaves as it does with no key: name matching only, answers checked against template rules only.
    Tests that exercise the Claude code paths pass a stand-in client explicitly.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
