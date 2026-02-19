"""Data models for Sentinel query results and metadata envelopes.

Provides typed dataclasses for incidents, alerts, trends, and entities,
plus QueryResult/QueryError wrappers and relative time formatting.
"""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


def format_relative_time(dt: datetime) -> str:
    """Format a datetime as a human-readable relative string.

    Examples: 'just now', '5 minutes ago', '2 hours ago',
    'yesterday at 3:14 PM', '3 days ago', 'Feb 18, 2026'

    Handles naive datetimes by assuming UTC.
    Uses %I:%M %p for cross-platform compatibility (not %-I which fails on Windows).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    delta = now - dt

    seconds = int(delta.total_seconds())
    if seconds < 0:
        # Future timestamps -- treat as "just now"
        return "just now"
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 172800:  # 2 days
        return f"yesterday at {dt.strftime('%I:%M %p').lstrip('0')}"
    elif seconds < 604800:  # 7 days
        days = seconds // 86400
        return f"{days} days ago"
    else:
        return dt.strftime("%b %d, %Y")


@dataclass
class QueryMetadata:
    """Metadata envelope for query results."""

    total: int
    query_ms: float
    truncated: bool
    partial_error: str | None = None


@dataclass
class QueryResult:
    """Wrapper for all successful query responses."""

    metadata: QueryMetadata
    results: list[Any]

    def to_dict(self) -> dict:
        """Serialize for LLM consumption."""
        return {
            "metadata": asdict(self.metadata),
            "results": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in self.results
            ],
        }


@dataclass
class QueryError:
    """Structured error for failed queries."""

    code: str
    message: str
    retry_possible: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Incident:
    """Projected fields for incident list and detail views.

    entity_count defaults to 0 in list view because SecurityIncident has no
    native entity data. Entity counts are computed from SecurityAlert.Entities
    which requires a cross-table join that would be too expensive for list
    queries. The field is populated with the actual count in get_incident_detail()
    from the entity sub-query results.
    """

    number: int
    title: str
    severity: str  # "High", "Medium", "Low", "Informational"
    status: str  # "New", "Active", "Closed"
    created_time: datetime
    last_modified_time: datetime
    description: str = ""
    owner: str = ""
    alert_count: int = 0
    entity_count: int = 0
    closed_time: datetime | None = None
    first_activity_time: datetime | None = None
    last_activity_time: datetime | None = None
    incident_url: str = ""
    classification: str = ""
    classification_reason: str = ""
    labels: list[str] | None = None
    created_time_ago: str = ""
    last_modified_time_ago: str = ""

    def to_dict(self) -> dict:
        """Convert to dict with datetimes as ISO strings."""
        d = asdict(self)
        for key in (
            "created_time",
            "last_modified_time",
            "closed_time",
            "first_activity_time",
            "last_activity_time",
        ):
            val = d.get(key)
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d


@dataclass
class Alert:
    """Projected fields for alert list views."""

    name: str  # AlertName
    display_name: str  # DisplayName
    severity: str  # AlertSeverity: "High", "Medium", "Low", "Informational"
    status: str
    time_generated: datetime
    description: str = ""
    tactics: str = ""
    techniques: str = ""
    provider_name: str = ""
    compromised_entity: str = ""
    system_alert_id: str = ""
    time_generated_ago: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        for key in ("time_generated",):
            val = d.get(key)
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d


@dataclass
class TrendPoint:
    """A single data point in an alert trend time series."""

    timestamp: datetime
    count: int
    severity: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "count": self.count,
            "severity": self.severity,
        }


@dataclass
class EntityCount:
    """A ranked entity with occurrence count."""

    entity_type: str  # "account", "ip", "host"
    entity_name: str  # The actual value (username, IP address, hostname)
    count: int

    def to_dict(self) -> dict:
        return asdict(self)
