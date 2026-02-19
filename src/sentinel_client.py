"""SentinelClient for executing KQL templates against a Sentinel workspace.

Wraps azure-monitor-query LogsQueryClient with typed result parsing,
severity filtering, metadata envelopes, and structured error handling.
All methods are read-only.
"""

import json
import logging
from datetime import UTC, datetime

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

from src.config import Settings
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
from src.projections import apply_projection
from src.queries import (
    MAX_LIMITS,
    TEMPLATE_TIMEOUTS,
    TIME_WINDOWS,
    build_query,
    severity_filter,
)

logger = logging.getLogger(__name__)


class SentinelClient:
    """Executes predefined KQL templates against a Sentinel workspace.

    All query methods return QueryResult on success or QueryError on failure.
    No freeform KQL is accepted -- only registered templates.
    """

    def __init__(self, settings: Settings, *, client: LogsQueryClient | None = None):
        """Initialize with Settings. Optionally inject a LogsQueryClient for testing.

        Args:
            settings: Application settings with sentinel_workspace_id.
            client: Optional pre-built LogsQueryClient (for test injection).
        """
        self._workspace_id = settings.sentinel_workspace_id
        if client is not None:
            self._client = client
        else:
            credential = DefaultAzureCredential()
            self._client = LogsQueryClient(credential)

    # ------------------------------------------------------------------
    # Private: query execution
    # ------------------------------------------------------------------

    def _execute_query(
        self,
        query: str,
        timespan,
        server_timeout: int,
    ) -> tuple[list, bool, str | None, float] | QueryError:
        """Execute a KQL query and return parsed results or QueryError.

        Returns:
            On success: (tables, is_partial, error_msg, query_ms)
            On failure: QueryError
        """
        try:
            response = self._client.query_workspace(
                workspace_id=self._workspace_id,
                query=query,
                timespan=timespan,
                server_timeout=server_timeout,
                include_statistics=True,
            )

            if response.status == LogsQueryStatus.SUCCESS:
                tables = response.tables
                query_ms = 0.0
                try:
                    if response.statistics:
                        query_ms = (
                            response.statistics.get("query", {}).get(
                                "executionTime", 0
                            )
                            * 1000
                        )
                except (AttributeError, TypeError):
                    query_ms = 0.0
                return (tables, False, None, query_ms)

            elif response.status == LogsQueryStatus.PARTIAL:
                tables = response.partial_data
                error = response.partial_error
                query_ms = 0.0
                try:
                    if response.statistics:
                        query_ms = (
                            response.statistics.get("query", {}).get(
                                "executionTime", 0
                            )
                            * 1000
                        )
                except (AttributeError, TypeError):
                    query_ms = 0.0
                error_msg = f"{error.code}: {error.message}" if error else "Partial results"
                return (tables, True, error_msg, query_ms)

            else:
                # Unexpected status -- defensive handling
                return QueryError(
                    code="unexpected_status",
                    message=f"Unexpected query status: {response.status}",
                    retry_possible=False,
                )

        except HttpResponseError as e:
            status_code = getattr(e.response, "status_code", 0) if e.response else 0
            error_code = getattr(e.error, "code", "http_error") if e.error else "http_error"
            retry_possible = status_code in (429, 500, 502, 503, 504)
            return QueryError(
                code=error_code,
                message=str(e)[:500],
                retry_possible=retry_possible,
            )

        except Exception as e:
            logger.exception("Unexpected error executing query")
            return QueryError(
                code="unknown",
                message=str(e)[:500],
                retry_possible=False,
            )

    # ------------------------------------------------------------------
    # Private: result parsing
    # ------------------------------------------------------------------

    def _parse_incidents(self, tables, is_detail: bool = False) -> list[Incident]:
        """Parse LogsTable rows into Incident dataclasses.

        Maps Sentinel column names to dataclass fields. entity_count is always
        set to 0 here because SecurityIncident has no entity data natively.
        It is populated later by get_incident_detail from entity sub-query results.
        """
        incidents = []
        if not tables:
            return incidents

        table = tables[0]
        columns = [col.name if hasattr(col, "name") else str(col) for col in table.columns]

        for row in table.rows:
            row_dict = dict(zip(columns, row, strict=False))

            # Parse owner from dynamic JSON field
            owner = ""
            raw_owner = row_dict.get("Owner", "")
            if raw_owner and isinstance(raw_owner, str):
                try:
                    owner_obj = json.loads(raw_owner)
                    owner = owner_obj.get("assignedTo", "") if isinstance(owner_obj, dict) else ""
                except (json.JSONDecodeError, TypeError):
                    owner = ""
            elif raw_owner and isinstance(raw_owner, dict):
                owner = raw_owner.get("assignedTo", "")

            # Parse AlertIds to get alert_count
            alert_count = 0
            raw_alerts = row_dict.get("AlertIds", "")
            if raw_alerts:
                if isinstance(raw_alerts, list):
                    alert_count = len(raw_alerts)
                elif isinstance(raw_alerts, str):
                    try:
                        parsed = json.loads(raw_alerts)
                        alert_count = len(parsed) if isinstance(parsed, list) else 0
                    except (json.JSONDecodeError, TypeError):
                        alert_count = 0

            # Parse datetime fields
            created_time = self._parse_datetime(row_dict.get("CreatedTime"))
            last_modified_time = self._parse_datetime(row_dict.get("LastModifiedTime"))

            incident_kwargs = {
                "number": int(row_dict.get("IncidentNumber", 0)),
                "title": str(row_dict.get("Title", "")),
                "severity": str(row_dict.get("Severity", "")),
                "status": str(row_dict.get("Status", "")),
                "created_time": created_time,
                "last_modified_time": last_modified_time,
                "description": str(row_dict.get("Description", "") or ""),
                "owner": owner,
                "alert_count": alert_count,
                "entity_count": 0,  # Populated by get_incident_detail only
                "created_time_ago": format_relative_time(created_time),
                "last_modified_time_ago": format_relative_time(last_modified_time),
            }

            # Detail-only fields
            if is_detail:
                incident_kwargs["closed_time"] = self._parse_datetime(
                    row_dict.get("ClosedTime")
                )
                incident_kwargs["first_activity_time"] = self._parse_datetime(
                    row_dict.get("FirstActivityTime")
                )
                incident_kwargs["last_activity_time"] = self._parse_datetime(
                    row_dict.get("LastActivityTime")
                )
                incident_kwargs["incident_url"] = str(row_dict.get("IncidentUrl", "") or "")
                incident_kwargs["classification"] = str(
                    row_dict.get("Classification", "") or ""
                )
                incident_kwargs["classification_reason"] = str(
                    row_dict.get("ClassificationReason", "") or ""
                )

                # Parse Labels from JSON array
                raw_labels = row_dict.get("Labels", "")
                labels = None
                if raw_labels:
                    if isinstance(raw_labels, list):
                        labels = [
                            (lbl.get("labelName", str(lbl)) if isinstance(lbl, dict) else str(lbl))
                            for lbl in raw_labels
                        ]
                    elif isinstance(raw_labels, str):
                        try:
                            parsed_labels = json.loads(raw_labels)
                            if isinstance(parsed_labels, list):
                                labels = [
                                    (
                                        lbl.get("labelName", str(lbl))
                                        if isinstance(lbl, dict)
                                        else str(lbl)
                                    )
                                    for lbl in parsed_labels
                                ]
                        except (json.JSONDecodeError, TypeError):
                            labels = None
                incident_kwargs["labels"] = labels

            incidents.append(Incident(**incident_kwargs))

        return incidents

    def _parse_alerts(self, tables) -> list[Alert]:
        """Parse LogsTable rows into Alert dataclasses.

        Uses AlertSeverity (NOT Severity) per SecurityAlert table schema.
        """
        alerts = []
        if not tables:
            return alerts

        table = tables[0]
        columns = [col.name if hasattr(col, "name") else str(col) for col in table.columns]

        for row in table.rows:
            row_dict = dict(zip(columns, row, strict=False))

            time_generated = self._parse_datetime(row_dict.get("TimeGenerated"))

            alert = Alert(
                name=str(row_dict.get("AlertName", "")),
                display_name=str(row_dict.get("DisplayName", "")),
                severity=str(row_dict.get("AlertSeverity", "")),
                status=str(row_dict.get("Status", "")),
                time_generated=time_generated,
                description=str(row_dict.get("Description", "") or ""),
                tactics=str(row_dict.get("Tactics", "") or ""),
                techniques=str(row_dict.get("Techniques", "") or ""),
                provider_name=str(row_dict.get("ProviderName", "") or ""),
                compromised_entity=str(row_dict.get("CompromisedEntity", "") or ""),
                system_alert_id=str(row_dict.get("SystemAlertId", "") or ""),
                time_generated_ago=format_relative_time(time_generated),
            )
            alerts.append(alert)

        return alerts

    def _parse_entities(self, tables) -> list[dict]:
        """Parse entity rows into simple dicts with entity_type and entity_name."""
        entities = []
        if not tables:
            return entities

        table = tables[0]
        columns = [col.name if hasattr(col, "name") else str(col) for col in table.columns]

        for row in table.rows:
            row_dict = dict(zip(columns, row, strict=False))
            entities.append(
                {
                    "entity_type": str(row_dict.get("EntityType", "")),
                    "entity_name": str(row_dict.get("EntityName", "")),
                }
            )

        return entities

    def _parse_trend_points(self, tables) -> list[TrendPoint]:
        """Parse LogsTable rows into TrendPoint dataclasses.

        Maps TimeGenerated->timestamp, Count->count, AlertSeverity->severity (if present).
        """
        points = []
        if not tables:
            return points

        table = tables[0]
        columns = [col.name if hasattr(col, "name") else str(col) for col in table.columns]

        for row in table.rows:
            row_dict = dict(zip(columns, row, strict=False))
            timestamp = self._parse_datetime(row_dict.get("TimeGenerated"))
            count = int(row_dict.get("Count", 0))
            severity = str(row_dict.get("AlertSeverity", ""))
            points.append(TrendPoint(timestamp=timestamp, count=count, severity=severity))

        return points

    def _parse_entity_counts(self, tables) -> list[EntityCount]:
        """Parse LogsTable rows into EntityCount dataclasses.

        Maps EntityType->entity_type, EntityName->entity_name, AlertCount->count.
        """
        entities = []
        if not tables:
            return entities

        table = tables[0]
        columns = [col.name if hasattr(col, "name") else str(col) for col in table.columns]

        for row in table.rows:
            row_dict = dict(zip(columns, row, strict=False))
            entities.append(
                EntityCount(
                    entity_type=str(row_dict.get("EntityType", "")),
                    entity_name=str(row_dict.get("EntityName", "")),
                    count=int(row_dict.get("AlertCount", 0)),
                )
            )

        return entities

    @staticmethod
    def _parse_datetime(value) -> datetime:
        """Parse a datetime value from LogsTable, handling various formats.

        Returns datetime with UTC timezone. Falls back to epoch start on failure.
        """
        if value is None:
            return datetime(1970, 1, 1, tzinfo=UTC)
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value
        if isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=UTC)
                return dt
            except (ValueError, TypeError):
                return datetime(1970, 1, 1, tzinfo=UTC)
        return datetime(1970, 1, 1, tzinfo=UTC)

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def query_incidents(
        self,
        time_window: str = "last_24h",
        min_severity: str = "Informational",
        limit: int = 20,
    ) -> QueryResult | QueryError:
        """Query security incidents filtered by severity and time range.

        entity_count will be 0 for all incidents in list view.

        Args:
            time_window: Predefined time window key (e.g., "last_24h").
            min_severity: Minimum severity threshold.
            limit: Max results to return (clamped to hard cap).

        Returns:
            QueryResult with Incident dataclasses or QueryError.
        """
        if time_window not in TIME_WINDOWS:
            return QueryError(
                code="invalid_time_window",
                message=f"Unknown time window: '{time_window}'. "
                f"Valid: {sorted(TIME_WINDOWS.keys())}",
                retry_possible=False,
            )

        # Clamp limit
        limit = min(limit, MAX_LIMITS["incident_list"])

        window = TIME_WINDOWS[time_window]
        query = build_query(
            "list_incidents",
            time_range=window["kql_ago"],
            severity_filter=severity_filter(min_severity),
            limit=limit,
        )

        timeout = TEMPLATE_TIMEOUTS.get("list_incidents", 60)
        result = self._execute_query(query, window["timespan"], timeout)

        if isinstance(result, QueryError):
            return result

        tables, is_partial, partial_error, query_ms = result
        incidents = self._parse_incidents(tables)

        # Apply projection
        projected = [apply_projection(inc.to_dict(), "incident_list") for inc in incidents]

        return QueryResult(
            metadata=QueryMetadata(
                total=len(projected),
                query_ms=query_ms,
                truncated=is_partial,
                partial_error=partial_error,
            ),
            results=projected,
        )

    def get_incident_detail(
        self,
        incident_ref: int | str,
    ) -> QueryResult | QueryError:
        """Get detailed incident info by number or name, including alerts and entities.

        When looking up by number (int), uses exact match.
        When looking up by name (str), uses case-insensitive substring match.
        entity_count is populated from the entity sub-query results.

        Args:
            incident_ref: Incident number (int) or title substring (str).

        Returns:
            QueryResult with composite {incidents, alerts, entities} or QueryError.
        """
        if isinstance(incident_ref, int):
            query = build_query(
                "get_incident_by_number",
                incident_number=incident_ref,
            )
            timeout = TEMPLATE_TIMEOUTS.get("get_incident_by_number", 60)
            # Use a wide time window for detail queries
            timespan = TIME_WINDOWS["last_30d"]["timespan"]
        else:
            query = build_query(
                "get_incident_by_name",
                incident_name=str(incident_ref),
                limit=10,
            )
            timeout = TEMPLATE_TIMEOUTS.get("get_incident_by_name", 60)
            timespan = TIME_WINDOWS["last_30d"]["timespan"]

        result = self._execute_query(query, timespan, timeout)
        if isinstance(result, QueryError):
            return result

        tables, is_partial, partial_error, query_ms = result
        incidents = self._parse_incidents(tables, is_detail=True)

        # For each found incident, fetch related alerts and entities
        all_alerts = []
        all_entities = []

        for incident in incidents:
            # Fetch alerts
            alerts_query = build_query(
                "get_incident_alerts",
                incident_number=incident.number,
            )
            alerts_result = self._execute_query(
                alerts_query,
                TIME_WINDOWS["last_30d"]["timespan"],
                TEMPLATE_TIMEOUTS.get("get_incident_alerts", 60),
            )
            if not isinstance(alerts_result, QueryError):
                a_tables, _, _, _ = alerts_result
                incident_alerts = self._parse_alerts(a_tables)
                all_alerts.extend(incident_alerts)

            # Fetch entities
            entities_query = build_query(
                "get_incident_entities",
                incident_number=incident.number,
            )
            entities_result = self._execute_query(
                entities_query,
                TIME_WINDOWS["last_30d"]["timespan"],
                TEMPLATE_TIMEOUTS.get("get_incident_entities", 60),
            )
            if not isinstance(entities_result, QueryError):
                e_tables, _, _, _ = entities_result
                incident_entities = self._parse_entities(e_tables)
                all_entities.extend(incident_entities)
                # Populate entity_count from sub-query results
                incident.entity_count = len(incident_entities)

        # Apply projection
        projected_incidents = [
            apply_projection(inc.to_dict(), "incident_detail") for inc in incidents
        ]
        projected_alerts = [
            apply_projection(a.to_dict(), "alert_list") for a in all_alerts
        ]

        return QueryResult(
            metadata=QueryMetadata(
                total=len(projected_incidents),
                query_ms=query_ms,
                truncated=is_partial,
                partial_error=partial_error,
            ),
            results=[
                {
                    "incidents": projected_incidents,
                    "alerts": projected_alerts,
                    "entities": all_entities,
                }
            ],
        )

    def query_alerts(
        self,
        time_window: str = "last_24h",
        min_severity: str = "Informational",
        limit: int = 20,
    ) -> QueryResult | QueryError:
        """Query security alerts filtered by severity and time range.

        Args:
            time_window: Predefined time window key.
            min_severity: Minimum severity threshold.
            limit: Max results to return (clamped to hard cap).

        Returns:
            QueryResult with Alert dataclasses or QueryError.
        """
        if time_window not in TIME_WINDOWS:
            return QueryError(
                code="invalid_time_window",
                message=f"Unknown time window: '{time_window}'. "
                f"Valid: {sorted(TIME_WINDOWS.keys())}",
                retry_possible=False,
            )

        # Clamp limit
        limit = min(limit, MAX_LIMITS["alert_list"])

        window = TIME_WINDOWS[time_window]
        query = build_query(
            "list_alerts",
            time_range=window["kql_ago"],
            severity_filter=severity_filter(min_severity),
            limit=limit,
        )

        timeout = TEMPLATE_TIMEOUTS.get("list_alerts", 60)
        result = self._execute_query(query, window["timespan"], timeout)

        if isinstance(result, QueryError):
            return result

        tables, is_partial, partial_error, query_ms = result
        alerts = self._parse_alerts(tables)

        # Apply projection
        projected = [apply_projection(a.to_dict(), "alert_list") for a in alerts]

        return QueryResult(
            metadata=QueryMetadata(
                total=len(projected),
                query_ms=query_ms,
                truncated=is_partial,
                partial_error=partial_error,
            ),
            results=projected,
        )

    # Bin size auto-selection: short windows get hourly bins, longer windows get daily bins
    _BIN_SIZE_MAP: dict[str, str] = {
        "last_1h": "1h",
        "last_24h": "1h",
        "last_3d": "1d",
        "last_7d": "1d",
        "last_14d": "1d",
        "last_30d": "1d",
    }

    def get_alert_trend(
        self,
        time_window: str = "last_7d",
        min_severity: str = "Informational",
        bin_size: str | None = None,
    ) -> QueryResult | QueryError:
        """Get alert trend data bucketed by time bins over a configurable period.

        Auto-selects bin_size if not provided: "1h" for short windows (last_1h,
        last_24h), "1d" for longer windows (last_3d and above).

        Args:
            time_window: Predefined time window key (e.g., "last_7d").
            min_severity: Minimum severity threshold.
            bin_size: Time bin granularity (e.g., "1h", "1d"). Auto-selected if None.

        Returns:
            QueryResult with TrendPoint dataclasses or QueryError.
        """
        if time_window not in TIME_WINDOWS:
            return QueryError(
                code="invalid_time_window",
                message=f"Unknown time window: '{time_window}'. "
                f"Valid: {sorted(TIME_WINDOWS.keys())}",
                retry_possible=False,
            )

        # Auto-select bin_size based on time_window
        if bin_size is None:
            bin_size = self._BIN_SIZE_MAP.get(time_window, "1d")

        window = TIME_WINDOWS[time_window]
        query = build_query(
            "alert_trend",
            time_range=window["kql_ago"],
            severity_filter=severity_filter(min_severity),
            bin_size=bin_size,
        )

        timeout = TEMPLATE_TIMEOUTS.get("alert_trend", 180)
        result = self._execute_query(query, window["timespan"], timeout)

        if isinstance(result, QueryError):
            return result

        tables, is_partial, partial_error, query_ms = result
        points = self._parse_trend_points(tables)

        return QueryResult(
            metadata=QueryMetadata(
                total=len(points),
                query_ms=query_ms,
                truncated=is_partial,
                partial_error=partial_error,
            ),
            results=points,
        )

    def get_top_entities(
        self,
        time_window: str = "last_7d",
        min_severity: str = "Informational",
        limit: int = 10,
    ) -> QueryResult | QueryError:
        """Get most-targeted entities ranked by alert count.

        Extracts entities from SecurityAlert.Entities JSON column using
        parse_json + mv-expand, filters to account/ip/host types, and
        aggregates by entity name.

        Args:
            time_window: Predefined time window key.
            min_severity: Minimum severity threshold.
            limit: Max entities to return (clamped to hard cap).

        Returns:
            QueryResult with EntityCount dataclasses or QueryError.
        """
        if time_window not in TIME_WINDOWS:
            return QueryError(
                code="invalid_time_window",
                message=f"Unknown time window: '{time_window}'. "
                f"Valid: {sorted(TIME_WINDOWS.keys())}",
                retry_possible=False,
            )

        # Clamp limit
        limit = min(limit, MAX_LIMITS["top_entities"])

        window = TIME_WINDOWS[time_window]
        query = build_query(
            "top_entities",
            time_range=window["kql_ago"],
            severity_filter=severity_filter(min_severity),
            limit=limit,
        )

        timeout = TEMPLATE_TIMEOUTS.get("top_entities", 180)
        result = self._execute_query(query, window["timespan"], timeout)

        if isinstance(result, QueryError):
            return result

        tables, is_partial, partial_error, query_ms = result
        entities = self._parse_entity_counts(tables)

        return QueryResult(
            metadata=QueryMetadata(
                total=len(entities),
                query_ms=query_ms,
                truncated=is_partial,
                partial_error=partial_error,
            ),
            results=entities,
        )
