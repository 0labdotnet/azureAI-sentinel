"""Tests for ToolDispatcher in src/tool_handlers.py."""

from unittest.mock import MagicMock

import pytest

from src.models import QueryError, QueryMetadata, QueryResult
from src.tool_handlers import ToolDispatcher


@pytest.fixture
def mock_client():
    """Create a mock SentinelClient with default successful responses."""
    client = MagicMock()

    # Default: return a successful QueryResult for all methods
    default_result = QueryResult(
        metadata=QueryMetadata(
            total=1, query_ms=50.0, truncated=False
        ),
        results=[{"test": "data"}],
    )
    client.query_incidents.return_value = default_result
    client.get_incident_detail.return_value = default_result
    client.query_alerts.return_value = default_result
    client.get_alert_trend.return_value = default_result
    client.get_top_entities.return_value = default_result

    return client


@pytest.fixture
def dispatcher(mock_client):
    """Create a ToolDispatcher with a mock client."""
    return ToolDispatcher(mock_client)


class TestDispatchRouting:
    """Test that dispatch routes to correct SentinelClient methods."""

    def test_query_incidents_routing(
        self, dispatcher, mock_client
    ):
        result = dispatcher.dispatch(
            "query_incidents", {"time_window": "last_24h"}
        )
        mock_client.query_incidents.assert_called_once_with(
            time_window="last_24h",
            min_severity="Informational",
            limit=20,
        )
        assert "metadata" in result
        assert "results" in result

    def test_get_incident_detail_int(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch(
            "get_incident_detail", {"incident_ref": 42}
        )
        mock_client.get_incident_detail.assert_called_once_with(
            incident_ref=42,
        )

    def test_get_incident_detail_string(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch(
            "get_incident_detail",
            {"incident_ref": "phishing"},
        )
        mock_client.get_incident_detail.assert_called_once_with(
            incident_ref="phishing",
        )

    def test_get_incident_detail_numeric_string_converts_to_int(
        self, dispatcher, mock_client
    ):
        """String "42" should be converted to int 42."""
        dispatcher.dispatch(
            "get_incident_detail", {"incident_ref": "42"}
        )
        mock_client.get_incident_detail.assert_called_once_with(
            incident_ref=42,
        )

    def test_get_incident_detail_missing_ref(self, dispatcher):
        result = dispatcher.dispatch(
            "get_incident_detail", {}
        )
        assert result == {
            "error": "Missing required parameter: incident_ref"
        }

    def test_query_alerts_routing(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch(
            "query_alerts",
            {
                "time_window": "last_7d",
                "min_severity": "High",
                "limit": 50,
            },
        )
        mock_client.query_alerts.assert_called_once_with(
            time_window="last_7d",
            min_severity="High",
            limit=50,
        )

    def test_get_alert_trend_routing(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch(
            "get_alert_trend",
            {"time_window": "last_7d", "bin_size": "1h"},
        )
        mock_client.get_alert_trend.assert_called_once_with(
            time_window="last_7d",
            min_severity="Informational",
            bin_size="1h",
        )

    def test_get_top_entities_routing(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch(
            "get_top_entities",
            {"time_window": "last_14d", "limit": 25},
        )
        mock_client.get_top_entities.assert_called_once_with(
            time_window="last_14d",
            min_severity="Informational",
            limit=25,
        )


class TestDispatchDefaults:
    """Test default argument values."""

    def test_query_incidents_defaults(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch("query_incidents", {})
        mock_client.query_incidents.assert_called_once_with(
            time_window="last_24h",
            min_severity="Informational",
            limit=20,
        )

    def test_get_alert_trend_defaults(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch("get_alert_trend", {})
        mock_client.get_alert_trend.assert_called_once_with(
            time_window="last_7d",
            min_severity="Informational",
            bin_size=None,
        )

    def test_get_top_entities_defaults(
        self, dispatcher, mock_client
    ):
        dispatcher.dispatch("get_top_entities", {})
        mock_client.get_top_entities.assert_called_once_with(
            time_window="last_7d",
            min_severity="Informational",
            limit=10,
        )


class TestUnknownTool:
    """Test unknown tool name handling."""

    def test_unknown_tool_returns_error_dict(self, dispatcher):
        result = dispatcher.dispatch("unknown_tool", {})
        assert result == {"error": "Unknown tool: unknown_tool"}

    def test_unknown_tool_does_not_raise(self, dispatcher):
        # Should not raise an exception
        dispatcher.dispatch("nonexistent", {"foo": "bar"})


class TestRetryLogic:
    """Test silent retry on retryable errors."""

    def test_retry_on_retryable_error_then_success(
        self, mock_client
    ):
        """First call returns retryable error, second returns success."""
        retryable_error = QueryError(
            code="throttled",
            message="Too many requests",
            retry_possible=True,
        )
        success_result = QueryResult(
            metadata=QueryMetadata(
                total=5, query_ms=100.0, truncated=False
            ),
            results=[{"incident": "data"}],
        )
        mock_client.query_incidents.side_effect = [
            retryable_error,
            success_result,
        ]
        dispatcher = ToolDispatcher(mock_client)

        result = dispatcher.dispatch(
            "query_incidents", {"time_window": "last_24h"}
        )
        assert mock_client.query_incidents.call_count == 2
        assert result == success_result.to_dict()

    def test_retry_exhaustion_returns_error(self, mock_client):
        """Both calls return retryable error -- return the second error."""
        error1 = QueryError(
            code="throttled",
            message="Too many requests",
            retry_possible=True,
        )
        error2 = QueryError(
            code="throttled",
            message="Still too many requests",
            retry_possible=True,
        )
        mock_client.query_incidents.side_effect = [error1, error2]
        dispatcher = ToolDispatcher(mock_client)

        result = dispatcher.dispatch(
            "query_incidents", {"time_window": "last_24h"}
        )
        assert mock_client.query_incidents.call_count == 2
        assert result == error2.to_dict()

    def test_non_retryable_error_no_retry(self, mock_client):
        """Non-retryable error should NOT trigger retry."""
        non_retryable = QueryError(
            code="invalid_query",
            message="Syntax error in KQL",
            retry_possible=False,
        )
        mock_client.query_incidents.return_value = non_retryable
        dispatcher = ToolDispatcher(mock_client)

        result = dispatcher.dispatch(
            "query_incidents", {"time_window": "last_24h"}
        )
        assert mock_client.query_incidents.call_count == 1
        assert result == non_retryable.to_dict()


class TestStatusMessages:
    """Test get_status_message method."""

    def test_query_incidents_status(self, dispatcher):
        msg = dispatcher.get_status_message("query_incidents")
        assert msg == "Querying incidents..."

    def test_get_incident_detail_status(self, dispatcher):
        msg = dispatcher.get_status_message("get_incident_detail")
        assert msg == "Looking up incident details..."

    def test_query_alerts_status(self, dispatcher):
        msg = dispatcher.get_status_message("query_alerts")
        assert msg == "Querying alerts..."

    def test_get_alert_trend_status(self, dispatcher):
        msg = dispatcher.get_status_message("get_alert_trend")
        assert msg == "Analyzing alert trends..."

    def test_get_top_entities_status(self, dispatcher):
        msg = dispatcher.get_status_message("get_top_entities")
        assert msg == "Finding top targeted entities..."

    def test_unknown_tool_status(self, dispatcher):
        msg = dispatcher.get_status_message("nonexistent_tool")
        assert isinstance(msg, str)
        assert len(msg) > 0
