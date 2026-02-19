"""Shared pytest fixtures for loading mock data and managing env vars."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import Settings


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


@pytest.fixture
def mock_settings():
    """Return a Settings instance with test values for Phase 3 testing."""
    return Settings(
        azure_openai_endpoint="https://test-resource.openai.azure.com/",
        azure_openai_api_key="test-api-key-12345",
        azure_openai_chat_deployment="gpt-4o",
        azure_openai_api_version="2024-10-21",
        sentinel_workspace_id="00000000-0000-0000-0000-000000000000",
        max_tool_rounds=5,
        max_turns=30,
    )


@pytest.fixture
def mock_openai_client():
    """Return a MagicMock simulating AzureOpenAI client behavior.

    Configured so client.chat.completions.create() returns a mock response
    with choices[0].message having content="Test response" and no tool_calls.
    """
    client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Test response"
    mock_message.tool_calls = None

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    client.chat.completions.create.return_value = mock_response
    return client


@pytest.fixture
def mock_sentinel_client():
    """Return a MagicMock of SentinelClient."""
    return MagicMock(spec=["query_incidents", "get_incident_detail",
                           "query_alerts", "get_alert_trend",
                           "get_top_entities"])
