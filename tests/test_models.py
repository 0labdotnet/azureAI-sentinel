"""Tests for data model serialization and format_relative_time utility."""

from datetime import UTC, datetime, timedelta

from src.models import (
    Alert,
    EntityCount,
    Incident,
    QueryError,
    QueryMetadata,
    QueryResult,
    TrendPoint,
    format_relative_time,
)


class TestIncident:
    """Tests for Incident dataclass."""

    def test_to_dict_converts_datetimes_to_iso(self):
        """Incident.to_dict() should convert datetime fields to ISO strings."""
        now = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        incident = Incident(
            number=42,
            title="Suspicious login",
            severity="High",
            status="New",
            created_time=now,
            last_modified_time=now,
        )
        d = incident.to_dict()
        assert d["created_time"] == "2026-02-18T10:30:00+00:00"
        assert d["last_modified_time"] == "2026-02-18T10:30:00+00:00"
        assert d["number"] == 42
        assert d["title"] == "Suspicious login"
        assert d["severity"] == "High"

    def test_to_dict_includes_entity_count(self):
        """Incident.to_dict() must include entity_count field."""
        now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
        incident = Incident(
            number=1,
            title="Test",
            severity="Low",
            status="Active",
            created_time=now,
            last_modified_time=now,
            entity_count=5,
        )
        d = incident.to_dict()
        assert "entity_count" in d
        assert d["entity_count"] == 5

    def test_entity_count_defaults_to_zero(self):
        """entity_count should default to 0 when not specified."""
        now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
        incident = Incident(
            number=1,
            title="Test",
            severity="Low",
            status="Active",
            created_time=now,
            last_modified_time=now,
        )
        assert incident.entity_count == 0

    def test_to_dict_handles_none_datetimes(self):
        """None datetime fields should remain None in the dict."""
        now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
        incident = Incident(
            number=1,
            title="Test",
            severity="Low",
            status="Active",
            created_time=now,
            last_modified_time=now,
            closed_time=None,
        )
        d = incident.to_dict()
        assert d["closed_time"] is None

    def test_to_dict_with_all_detail_fields(self):
        """Full detail incident should serialize all fields including entity_count."""
        now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
        incident = Incident(
            number=100,
            title="Brute force attack",
            severity="High",
            status="Active",
            created_time=now,
            last_modified_time=now,
            description="Multiple failed logins detected",
            owner="analyst@contoso.com",
            alert_count=3,
            entity_count=7,
            closed_time=None,
            first_activity_time=now - timedelta(hours=2),
            last_activity_time=now,
            incident_url="https://portal.azure.com/#/incident/100",
            classification="TruePositive",
            classification_reason="SuspiciousActivity",
            labels=["phishing", "external"],
            created_time_ago="2 hours ago",
            last_modified_time_ago="just now",
        )
        d = incident.to_dict()
        assert d["entity_count"] == 7
        assert d["alert_count"] == 3
        assert d["labels"] == ["phishing", "external"]
        assert d["classification"] == "TruePositive"
        assert isinstance(d["first_activity_time"], str)


class TestAlert:
    """Tests for Alert dataclass."""

    def test_to_dict_converts_time_generated(self):
        """Alert.to_dict() should convert time_generated to ISO string."""
        now = datetime(2026, 2, 18, 14, 0, 0, tzinfo=UTC)
        alert = Alert(
            name="Suspicious_Login",
            display_name="Suspicious Login",
            severity="Medium",
            status="New",
            time_generated=now,
        )
        d = alert.to_dict()
        assert d["time_generated"] == "2026-02-18T14:00:00+00:00"
        assert d["name"] == "Suspicious_Login"


class TestQueryResult:
    """Tests for QueryResult wrapper."""

    def test_to_dict_serializes_nested_incidents(self):
        """QueryResult.to_dict() should call to_dict() on nested results."""
        now = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)
        incidents = [
            Incident(
                number=1,
                title="Test 1",
                severity="High",
                status="New",
                created_time=now,
                last_modified_time=now,
                entity_count=0,
            ),
            Incident(
                number=2,
                title="Test 2",
                severity="Low",
                status="Active",
                created_time=now,
                last_modified_time=now,
                entity_count=3,
            ),
        ]
        result = QueryResult(
            metadata=QueryMetadata(total=2, query_ms=45.3, truncated=False),
            results=incidents,
        )
        d = result.to_dict()
        assert d["metadata"]["total"] == 2
        assert d["metadata"]["query_ms"] == 45.3
        assert d["metadata"]["truncated"] is False
        assert len(d["results"]) == 2
        assert d["results"][0]["number"] == 1
        assert d["results"][0]["entity_count"] == 0
        assert d["results"][1]["entity_count"] == 3
        # Datetimes should be ISO strings
        assert isinstance(d["results"][0]["created_time"], str)

    def test_to_dict_handles_plain_dicts(self):
        """QueryResult.to_dict() should handle results without to_dict() method."""
        result = QueryResult(
            metadata=QueryMetadata(total=1, query_ms=10.0, truncated=False),
            results=[{"key": "value"}],
        )
        d = result.to_dict()
        assert d["results"][0] == {"key": "value"}


class TestQueryError:
    """Tests for QueryError dataclass."""

    def test_to_dict(self):
        """QueryError.to_dict() should return all fields."""
        error = QueryError(
            code="workspace_not_found",
            message="Workspace ID not found",
            retry_possible=False,
        )
        d = error.to_dict()
        assert d["code"] == "workspace_not_found"
        assert d["message"] == "Workspace ID not found"
        assert d["retry_possible"] is False

    def test_to_dict_retry_possible(self):
        """QueryError with retry_possible=True should serialize correctly."""
        error = QueryError(code="timeout", message="Query timed out", retry_possible=True)
        d = error.to_dict()
        assert d["retry_possible"] is True


class TestTrendPoint:
    """Tests for TrendPoint dataclass."""

    def test_to_dict(self):
        ts = datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
        point = TrendPoint(timestamp=ts, count=15, severity="High")
        d = point.to_dict()
        assert d["timestamp"] == "2026-02-18T00:00:00+00:00"
        assert d["count"] == 15
        assert d["severity"] == "High"


class TestEntityCount:
    """Tests for EntityCount dataclass."""

    def test_to_dict(self):
        entity = EntityCount(entity_type="account", entity_name="admin@contoso.com", count=42)
        d = entity.to_dict()
        assert d["entity_type"] == "account"
        assert d["entity_name"] == "admin@contoso.com"
        assert d["count"] == 42


class TestFormatRelativeTime:
    """Tests for format_relative_time() utility."""

    def test_just_now(self):
        """Timestamps less than 60 seconds ago should return 'just now'."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(seconds=30))
        assert result == "just now"

    def test_minutes_ago_singular(self):
        """1 minute ago should use singular form."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(minutes=1, seconds=10))
        assert result == "1 minute ago"

    def test_minutes_ago_plural(self):
        """Multiple minutes ago should use plural form."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(minutes=5))
        assert result == "5 minutes ago"

    def test_hours_ago_singular(self):
        """1 hour ago should use singular form."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(hours=1, minutes=10))
        assert result == "1 hour ago"

    def test_hours_ago_plural(self):
        """Multiple hours ago should use plural form."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(hours=3))
        assert result == "3 hours ago"

    def test_yesterday(self):
        """Timestamps between 1-2 days ago should show 'yesterday at HH:MM AM/PM'."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(hours=30)
        result = format_relative_time(yesterday)
        assert result.startswith("yesterday at ")
        # Should contain AM or PM
        assert "AM" in result or "PM" in result

    def test_days_ago(self):
        """Timestamps 2-7 days ago should show 'N days ago'."""
        now = datetime.now(UTC)
        result = format_relative_time(now - timedelta(days=3))
        assert result == "3 days ago"

    def test_older_dates(self):
        """Timestamps 7+ days ago should show 'Mon DD, YYYY' format."""
        old = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)
        result = format_relative_time(old)
        assert result == "Jan 05, 2026"

    def test_naive_datetime_assumed_utc(self):
        """Naive datetimes should be treated as UTC without errors."""
        # Use utcnow-equivalent to create a naive datetime that is actually
        # 5 minutes ago in UTC (datetime.now() returns local time which may
        # differ from UTC by hours).
        now_utc = datetime.now(UTC)
        naive = now_utc.replace(tzinfo=None) - timedelta(minutes=5)
        result = format_relative_time(naive)
        # Should not raise and should contain 'minutes ago'
        assert "minutes ago" in result or "minute ago" in result
