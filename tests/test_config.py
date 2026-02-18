"""Unit tests for config validation and error handling."""

from unittest.mock import MagicMock, patch

import openai

from src.config import (
    Settings,
    load_settings,
    test_openai_connectivity,
    test_sentinel_connectivity,
    validate_env_vars,
)


class TestValidateEnvVars:
    """Tests for environment variable validation."""

    def test_validate_env_vars_all_present(self, mock_env_vars):
        """When all required vars are set, all should pass."""
        passed, failed = validate_env_vars()
        assert len(passed) == 3
        assert len(failed) == 0
        assert "AZURE_OPENAI_ENDPOINT" in passed
        assert "AZURE_OPENAI_API_KEY" in passed
        assert "SENTINEL_WORKSPACE_ID" in passed

    def test_validate_env_vars_all_missing(self, clean_env):
        """When no required vars are set, all should fail."""
        passed, failed = validate_env_vars()
        assert len(passed) == 0
        assert len(failed) == 3

    def test_validate_env_vars_partial(self, clean_env, monkeypatch):
        """When some vars are set, should report correct pass/fail split."""
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
        passed, failed = validate_env_vars()
        assert len(passed) == 1
        assert len(failed) == 2
        assert "AZURE_OPENAI_ENDPOINT" in passed


class TestLoadSettings:
    """Tests for settings loading from environment."""

    def test_load_settings_from_env(self, mock_env_vars):
        """Settings fields should be populated from env vars."""
        settings = load_settings()
        assert settings.azure_openai_endpoint == "https://test-resource.openai.azure.com/"
        assert settings.azure_openai_api_key == "test-api-key-12345"
        assert settings.sentinel_workspace_id == "00000000-0000-0000-0000-000000000000"

    def test_load_settings_defaults(self, clean_env):
        """Default values should be applied for optional fields."""
        settings = load_settings()
        assert settings.azure_openai_chat_deployment == "gpt-4o"
        assert settings.azure_openai_api_version == "2024-10-21"


class TestOpenAIConnectivity:
    """Tests for Azure OpenAI connectivity checking."""

    def test_openai_connectivity_success(self):
        """Successful connection should return True and connected message."""
        mock_choice = MagicMock()
        mock_choice.finish_reason = "stop"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("src.config.AzureOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_client_cls.return_value = mock_client

            settings = Settings(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
            )
            success, message = test_openai_connectivity(settings)

        assert success is True
        assert message == "Azure OpenAI connected"

    def test_openai_connectivity_content_filter_input(self):
        """Content filter on input should return specific actionable message."""
        with patch("src.config.AzureOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            error = openai.BadRequestError(
                message="Content filter triggered",
                response=MagicMock(status_code=400),
                body={"code": "content_filter"},
            )
            error.code = "content_filter"
            mock_client.chat.completions.create.side_effect = error
            mock_client_cls.return_value = mock_client

            settings = Settings(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
            )
            success, message = test_openai_connectivity(settings)

        assert success is False
        assert "Content filter modification pending" in message
        assert "approval required" in message

    def test_openai_connectivity_content_filter_output(self):
        """Content filter on output (finish_reason) should return specific message."""
        mock_choice = MagicMock()
        mock_choice.finish_reason = "content_filter"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch("src.config.AzureOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_client_cls.return_value = mock_client

            settings = Settings(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="test-key",
            )
            success, message = test_openai_connectivity(settings)

        assert success is False
        assert "Content filter modification pending" in message

    def test_openai_connectivity_auth_error(self):
        """Authentication error should return specific auth message."""
        with patch("src.config.AzureOpenAI") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
            mock_client_cls.return_value = mock_client

            settings = Settings(
                azure_openai_endpoint="https://test.openai.azure.com/",
                azure_openai_api_key="bad-key",
            )
            success, message = test_openai_connectivity(settings)

        assert success is False
        assert "authentication failed" in message
        assert "API key" in message


class TestSentinelConnectivity:
    """Tests for Sentinel workspace connectivity checking."""

    def test_sentinel_connectivity_success(self):
        """Successful query should return True and connected message."""
        from azure.monitor.query import LogsQueryStatus

        mock_response = MagicMock()
        mock_response.status = LogsQueryStatus.SUCCESS

        with (
            patch("src.config.DefaultAzureCredential"),
            patch("src.config.LogsQueryClient") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.query_workspace.return_value = mock_response
            mock_client_cls.return_value = mock_client

            settings = Settings(
                sentinel_workspace_id="00000000-0000-0000-0000-000000000000",
            )
            success, message = test_sentinel_connectivity(settings)

        assert success is True
        assert "Sentinel connected" in message

    def test_sentinel_connectivity_auth_error(self):
        """Auth error should suggest az login."""
        with (
            patch("src.config.DefaultAzureCredential"),
            patch("src.config.LogsQueryClient") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client.query_workspace.side_effect = Exception(
                "AuthenticationError: No credential could be found"
            )
            mock_client_cls.return_value = mock_client

            settings = Settings(
                sentinel_workspace_id="00000000-0000-0000-0000-000000000000",
            )
            success, message = test_sentinel_connectivity(settings)

        assert success is False
        assert "az login" in message
