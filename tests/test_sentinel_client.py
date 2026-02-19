"""Unit tests for SentinelClient with mocked LogsQueryClient.

Uses mock objects to simulate LogsTable responses without live Azure calls.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

from src.config import Settings
from src.models import QueryError, QueryResult
from src.sentinel_client import SentinelClient

# --------------------------------------------------------------------------
# Mock helpers
# --------------------------------------------------------------------------


def _extract_query(call_args) -> str:
    """Extract the KQL query string from a mock call_args object."""
    return (
        call_args.kwargs.get("query")
        or call_args[1].get(
            "query", call_args[0][1] if len(call_args[0]) > 1 else ""
        )
    )


class MockColumn:
    """Mimics a LogsTable column with a name attribute."""

    def __init__(self, name: str):
        self.name = name


class MockLogsTable:
    """Mimics LogsTable with columns and rows.

    Rows are lists of values aligned with column order.
    """

    def __init__(self, columns: list[str], rows: list[list]):
        self.columns = [MockColumn(c) for c in columns]
        self.rows = rows


class MockResponse:
    """Mimics LogsQueryResult/LogsQueryPartialResult."""

    def __init__(
        self,
        status: LogsQueryStatus,
        tables: list | None = None,
        statistics: dict | None = None,
        partial_data: list | None = None,
        partial_error: object | None = None,
    ):
        self.status = status
        self.tables = tables or []
        self.statistics = statistics
        self.partial_data = partial_data or []
        self.partial_error = partial_error


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _make_settings() -> Settings:
    """Create test settings."""
    return Settings(
        sentinel_workspace_id="00000000-0000-0000-0000-000000000000",
    )


def _make_incident_table(
    count: int = 2,
    is_detail: bool = False,
) -> MockLogsTable:
    """Create a mock SecurityIncident LogsTable."""
    columns = [
        "IncidentNumber",
        "Title",
        "Severity",
        "Status",
        "CreatedTime",
        "LastModifiedTime",
        "Owner",
        "AlertIds",
        "Description",
        "FirstActivityTime",
        "LastActivityTime",
    ]
    if is_detail:
        columns.extend([
            "ClosedTime",
            "Labels",
            "Classification",
            "ClassificationReason",
            "IncidentUrl",
        ])

    now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
    rows = []
    for i in range(1, count + 1):
        row = [
            i,  # IncidentNumber
            f"Test Incident {i}",  # Title
            "High" if i == 1 else "Medium",  # Severity
            "New",  # Status
            (now - timedelta(hours=i)).isoformat(),  # CreatedTime
            now.isoformat(),  # LastModifiedTime
            json.dumps({"assignedTo": f"analyst{i}@contoso.com"}),  # Owner
            json.dumps([f"alert-{i}-a", f"alert-{i}-b"]),  # AlertIds
            f"Description for incident {i}",  # Description
            (now - timedelta(hours=i + 1)).isoformat(),  # FirstActivityTime
            now.isoformat(),  # LastActivityTime
        ]
        if is_detail:
            row.extend([
                None,  # ClosedTime
                json.dumps([{"labelName": "critical"}, {"labelName": "external"}]),  # Labels
                "TruePositive",  # Classification
                "SuspiciousActivity",  # ClassificationReason
                f"https://portal.azure.com/#/incident/{i}",  # IncidentUrl
            ])
        rows.append(row)

    return MockLogsTable(columns, rows)


def _make_alert_table(count: int = 2) -> MockLogsTable:
    """Create a mock SecurityAlert LogsTable."""
    columns = [
        "AlertName",
        "DisplayName",
        "AlertSeverity",
        "Status",
        "TimeGenerated",
        "Description",
        "Tactics",
        "Techniques",
        "ProviderName",
        "CompromisedEntity",
        "SystemAlertId",
    ]

    now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
    rows = []
    for i in range(1, count + 1):
        rows.append([
            f"Alert_{i}",  # AlertName
            f"Suspicious Activity {i}",  # DisplayName
            "High",  # AlertSeverity
            "New",  # Status
            (now - timedelta(hours=i)).isoformat(),  # TimeGenerated
            f"Alert description {i}",  # Description
            "InitialAccess",  # Tactics
            "T1078",  # Techniques
            "Microsoft Defender",  # ProviderName
            f"user{i}@contoso.com",  # CompromisedEntity
            f"sys-alert-{i}",  # SystemAlertId
        ])

    return MockLogsTable(columns, rows)


def _make_entity_table() -> MockLogsTable:
    """Create a mock entity results table."""
    columns = ["EntityType", "EntityName"]
    rows = [
        ["account", "admin@contoso.com"],
        ["ip", "10.0.0.1"],
        ["host", "workstation-01"],
    ]
    return MockLogsTable(columns, rows)


@pytest.fixture
def mock_client():
    """Create a SentinelClient with a mocked LogsQueryClient."""
    mock_logs_client = MagicMock(spec=LogsQueryClient)
    settings = _make_settings()
    return SentinelClient(settings, client=mock_logs_client), mock_logs_client


# --------------------------------------------------------------------------
# Tests: query_incidents
# --------------------------------------------------------------------------


class TestQueryIncidents:
    """Tests for SentinelClient.query_incidents()."""

    def test_returns_query_result_with_incidents(self, mock_client):
        """query_incidents should return QueryResult with projected incident dicts."""
        client, mock_logs = mock_client
        incident_table = _make_incident_table(count=2)

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.SUCCESS,
            tables=[incident_table],
            statistics={"query": {"executionTime": 0.045}},
        )

        result = client.query_incidents(time_window="last_24h")

        assert isinstance(result, QueryResult)
        assert result.metadata.total == 2
        assert result.metadata.query_ms == pytest.approx(45.0)
        assert result.metadata.truncated is False
        assert len(result.results) == 2
        # Check projected fields exist
        assert result.results[0]["number"] == 1
        assert result.results[0]["title"] == "Test Incident 1"
        assert result.results[0]["severity"] == "High"
        # entity_count should be 0 in list view
        assert result.results[0]["entity_count"] == 0
        assert result.results[1]["entity_count"] == 0

    def test_severity_filter_in_kql(self, mock_client):
        """Severity filter should appear in the KQL query string."""
        client, mock_logs = mock_client

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.SUCCESS,
            tables=[_make_incident_table(count=1)],
            statistics=None,
        )

        client.query_incidents(min_severity="Medium")

        # Verify the KQL query passed to query_workspace
        call_args = mock_logs.query_workspace.call_args
        query = _extract_query(call_args)
        assert "'Medium','High'" in query

    def test_invalid_time_window_returns_error(self, mock_client):
        """Invalid time window should return QueryError."""
        client, _ = mock_client
        result = client.query_incidents(time_window="last_99d")
        assert isinstance(result, QueryError)
        assert result.code == "invalid_time_window"
        assert result.retry_possible is False

    def test_limit_clamping(self, mock_client):
        """Limit should be clamped to MAX_LIMITS."""
        client, mock_logs = mock_client

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.SUCCESS,
            tables=[_make_incident_table(count=1)],
            statistics=None,
        )

        client.query_incidents(limit=500)

        # Verify the limit in the KQL query is clamped to 100 (MAX_LIMITS["incident_list"])
        call_args = mock_logs.query_workspace.call_args
        query = _extract_query(call_args)
        assert "take 100" in query


# --------------------------------------------------------------------------
# Tests: get_incident_detail
# --------------------------------------------------------------------------


class TestGetIncidentDetail:
    """Tests for SentinelClient.get_incident_detail()."""

    def test_by_number_returns_detail_with_alerts_and_entities(self, mock_client):
        """get_incident_detail(int) should return incident with alerts and entities.

        entity_count should be populated from the entity sub-query.
        """
        client, mock_logs = mock_client

        detail_table = _make_incident_table(count=1, is_detail=True)
        alert_table = _make_alert_table(count=2)
        entity_table = _make_entity_table()

        # First call: incident detail, second: alerts, third: entities
        mock_logs.query_workspace.side_effect = [
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[detail_table],
                statistics={"query": {"executionTime": 0.050}},
            ),
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[alert_table],
                statistics=None,
            ),
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[entity_table],
                statistics=None,
            ),
        ]

        result = client.get_incident_detail(42)

        assert isinstance(result, QueryResult)
        assert result.metadata.total == 1
        composite = result.results[0]
        assert "incidents" in composite
        assert "alerts" in composite
        assert "entities" in composite
        assert len(composite["incidents"]) == 1
        assert len(composite["alerts"]) == 2
        assert len(composite["entities"]) == 3

        # entity_count should be populated from entity sub-query count
        incident = composite["incidents"][0]
        assert incident["entity_count"] == 3

        # Check detail fields are present
        assert "classification" in incident
        assert "labels" in incident
        assert incident["labels"] == ["critical", "external"]
        assert incident["classification"] == "TruePositive"

    def test_by_name_uses_contains_template(self, mock_client):
        """get_incident_detail(str) should use get_incident_by_name template."""
        client, mock_logs = mock_client

        detail_table = _make_incident_table(count=1, is_detail=True)

        mock_logs.query_workspace.side_effect = [
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[detail_table],
                statistics=None,
            ),
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[_make_alert_table(count=0)],
                statistics=None,
            ),
            MockResponse(
                status=LogsQueryStatus.SUCCESS,
                tables=[MockLogsTable(["EntityType", "EntityName"], [])],
                statistics=None,
            ),
        ]

        result = client.get_incident_detail("phishing")

        assert isinstance(result, QueryResult)
        # Verify the KQL query used 'contains'
        first_call = mock_logs.query_workspace.call_args_list[0]
        query = _extract_query(first_call)
        assert 'contains "phishing"' in query


# --------------------------------------------------------------------------
# Tests: query_alerts
# --------------------------------------------------------------------------


class TestQueryAlerts:
    """Tests for SentinelClient.query_alerts()."""

    def test_returns_query_result_with_alerts(self, mock_client):
        """query_alerts should return QueryResult with projected alert dicts."""
        client, mock_logs = mock_client

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.SUCCESS,
            tables=[_make_alert_table(count=3)],
            statistics={"query": {"executionTime": 0.032}},
        )

        result = client.query_alerts(time_window="last_7d", min_severity="High")

        assert isinstance(result, QueryResult)
        assert result.metadata.total == 3
        assert result.metadata.truncated is False
        assert len(result.results) == 3
        assert result.results[0]["name"] == "Alert_1"
        assert result.results[0]["display_name"] == "Suspicious Activity 1"
        assert result.results[0]["severity"] == "High"

    def test_invalid_time_window_returns_error(self, mock_client):
        """Invalid time window for alerts should return QueryError."""
        client, _ = mock_client
        result = client.query_alerts(time_window="invalid")
        assert isinstance(result, QueryError)
        assert result.code == "invalid_time_window"


# --------------------------------------------------------------------------
# Tests: partial results
# --------------------------------------------------------------------------


class TestPartialResults:
    """Tests for partial result handling."""

    def test_partial_results_set_truncated_flag(self, mock_client):
        """Partial results should set truncated=True and include partial_error."""
        client, mock_logs = mock_client

        partial_error = MagicMock()
        partial_error.code = "PartialError"
        partial_error.message = "Query timed out but returned partial data"

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.PARTIAL,
            partial_data=[_make_incident_table(count=1)],
            partial_error=partial_error,
            statistics={"query": {"executionTime": 0.180}},
        )

        result = client.query_incidents()

        assert isinstance(result, QueryResult)
        assert result.metadata.truncated is True
        assert "PartialError" in result.metadata.partial_error
        assert "Query timed out" in result.metadata.partial_error


# --------------------------------------------------------------------------
# Tests: error handling
# --------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling in SentinelClient."""

    def test_http_error_returns_query_error(self, mock_client):
        """HttpResponseError should return QueryError with appropriate code."""
        client, mock_logs = mock_client

        error = HttpResponseError(message="Too many requests")
        error.response = MagicMock()
        error.response.status_code = 429
        error.error = MagicMock()
        error.error.code = "TooManyRequests"

        mock_logs.query_workspace.side_effect = error

        result = client.query_incidents()

        assert isinstance(result, QueryError)
        assert result.code == "TooManyRequests"
        assert result.retry_possible is True

    def test_http_400_not_retryable(self, mock_client):
        """400 errors should not be retryable."""
        client, mock_logs = mock_client

        error = HttpResponseError(message="Bad request")
        error.response = MagicMock()
        error.response.status_code = 400
        error.error = MagicMock()
        error.error.code = "BadRequest"

        mock_logs.query_workspace.side_effect = error

        result = client.query_incidents()

        assert isinstance(result, QueryError)
        assert result.code == "BadRequest"
        assert result.retry_possible is False

    def test_general_exception_returns_query_error(self, mock_client):
        """General exceptions should return QueryError with unknown code."""
        client, mock_logs = mock_client
        mock_logs.query_workspace.side_effect = RuntimeError("Something unexpected")

        result = client.query_incidents()

        assert isinstance(result, QueryError)
        assert result.code == "unknown"
        assert "Something unexpected" in result.message
        assert result.retry_possible is False

    def test_limit_clamping_alerts(self, mock_client):
        """Alert limit should be clamped to MAX_LIMITS['alert_list']."""
        client, mock_logs = mock_client

        mock_logs.query_workspace.return_value = MockResponse(
            status=LogsQueryStatus.SUCCESS,
            tables=[_make_alert_table(count=1)],
            statistics=None,
        )

        client.query_alerts(limit=999)

        call_args = mock_logs.query_workspace.call_args
        query = _extract_query(call_args)
        assert "take 100" in query
