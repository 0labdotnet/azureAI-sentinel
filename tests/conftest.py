"""Shared pytest fixtures for loading mock data and managing env vars."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir():
    """Return the path to the tests/fixtures/ directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def chat_completion_fixture(fixtures_dir):
    """Load the mock chat completion response."""
    with open(fixtures_dir / "chat_completion.json") as f:
        return json.load(f)


@pytest.fixture
def tool_call_fixture(fixtures_dir):
    """Load the mock tool call response."""
    with open(fixtures_dir / "tool_call_response.json") as f:
        return json.load(f)


@pytest.fixture
def content_filter_error_fixture(fixtures_dir):
    """Load the mock content filter error response."""
    with open(fixtures_dir / "content_filter_error.json") as f:
        return json.load(f)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set required env vars to test values."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test-resource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("SENTINEL_WORKSPACE_ID", "00000000-0000-0000-0000-000000000000")


@pytest.fixture
def clean_env(monkeypatch):
    """Clear all AZURE_* and SENTINEL_* env vars and prevent .env reload."""
    env_prefixes = ("AZURE_", "SENTINEL_")
    import os

    for key in list(os.environ.keys()):
        if key.startswith(env_prefixes):
            monkeypatch.delenv(key, raising=False)

    # Prevent load_dotenv() from re-reading .env file during tests
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **kw: None)
