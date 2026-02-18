# Phase 2: Sentinel Data Access - Research

**Researched:** 2026-02-18
**Domain:** KQL query templates, azure-monitor-query SDK, Sentinel table schemas, retry/resilience patterns
**Confidence:** HIGH

## Summary

Phase 2 builds the Sentinel data access layer: a KQL template registry organized by domain (incidents, alerts, trends, entities), a `SentinelClient` class that executes these templates via `azure-monitor-query` v2.0.0 `LogsQueryClient`, and typed dataclass results wrapped in a metadata envelope. The phase covers five requirements (QUERY-01 through QUERY-05) that together enable natural-language querying of live Sentinel data.

The `azure-monitor-query` v2.0.0 SDK is already installed (verified in the project venv). It provides `LogsQueryClient.query_workspace()` for single queries and `LogsQueryClient.query_batch()` for batching multiple KQL queries in a single API call. The SDK's built-in retry policy (via `azure-core` v1.38.2) already handles HTTP 429 with exponential backoff (3 retries, 0.8s base, 60s max), so the application-level retry logic should focus on timeout handling and structured error surfacing rather than reimplementing backoff.

The SecurityIncident table has exactly four severity values: `Informational`, `Low`, `Medium`, `High` -- there is NO `Critical` severity in Sentinel incidents. This is confirmed by official Microsoft documentation. The SecurityAlert table uses `AlertSeverity` (not `Severity`) with the same four values. Entity data in SecurityAlert is stored as a JSON string in the `Entities` column and must be parsed with `parse_json()` + `mv-expand` in KQL. The SecurityIncident table logs a new row on every modification, so queries must use `summarize arg_max(LastModifiedTime, *) by IncidentNumber` to deduplicate and get the latest state of each incident.

**Primary recommendation:** Build the template registry as per-domain Python modules under `src/queries/`, use `LogsQueryClient.query_workspace()` with `server_timeout` configured per template category (60s for simple lookups, 180s for aggregations), and let `azure-core`'s built-in retry policy handle 429/5xx retries. Focus application logic on result parsing (LogsTable -> dataclass), partial result handling, and the metadata envelope pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Time ranges use predefined windows only: 'last_1h', 'last_24h', 'last_7d', 'last_30d' -- no freeform datetime parsing
- Severity filtering uses a minimum threshold model (e.g., 'Medium' returns Medium + High + Critical)
- Severity is optional with a default of 'Informational' (returns all severities when omitted)
- Incident detail lookups accept either incident number (integer) or incident name/title (string match)
- Query results returned as typed dataclasses (e.g., Incident, Alert, TrendPoint)
- Incident lists include summary + counts: number, title, severity, status, created time, alert count, entity count, last update time
- Timestamps formatted as human-readable relative strings (e.g., '2 hours ago', 'yesterday at 3:14 PM')
- Every query result wrapped in a metadata envelope: {metadata: {total, query_ms, truncated}, results: [...]}
- Templates organized in per-domain modules (incidents.py, alerts.py, trends.py, entities.py)
- Parameter substitution uses named placeholders with a builder function that validates params, applies defaults, and substitutes safely
- Field projections managed via a separate projection config (not baked into KQL templates) -- allows templates to return full rows, with projection applied post-query
- Result limits are caller-controlled with a hard cap and a sensible default when caller doesn't specify
- Standard retry: 3 retries with exponential backoff (1s, 2s, 4s) on transient failures (network errors, 5xx, 429)
- Partial results: return whatever came back with a 'truncated' flag in metadata -- LLM tells user results may be incomplete
- Timeouts: per-template configuration (trend/aggregation queries get longer timeouts than simple lookups)
- Errors surfaced as structured error objects with code, message, and retry_possible flag -- when retry is not possible, the LLM must pass error code + message directly to the user

### Claude's Discretion
- Exact predefined time window set (whether to include last_3d, last_14d, etc.)
- Default and max result limits per query type
- Specific dataclass field names and serialization format
- Exact backoff timing and jitter strategy
- How incident name matching works (substring, fuzzy, exact)
- Projection config format and location

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUERY-01 | User can ask natural language questions about security incidents and receive accurate results from Sentinel | SecurityIncident table schema verified, KQL query patterns for filtering by severity/time documented, deduplication pattern (`arg_max`) identified, dataclass projection fields defined |
| QUERY-02 | User can drill down into a specific incident by number to see detailed information including related alerts and entities | IncidentNumber field confirmed as `int` type, AlertIds field is `dynamic` (JSON array), entity extraction requires join to SecurityAlert + `parse_json(Entities)` + `mv-expand` |
| QUERY-03 | User can query security alerts filtered by severity and time range | SecurityAlert table schema verified, severity column is `AlertSeverity` (not `Severity`), entity types documented, projection fields identified |
| QUERY-04 | User can ask about alert trends over the past 7 days and receive a summarized analysis | `summarize ... by bin(TimeGenerated, 1d)` pattern documented for trends, `make-series` alternative researched for gap-filling, server_timeout=180 recommended for aggregation queries |
| QUERY-05 | User can ask which entities (users, IPs, hosts) have been most targeted and receive a ranked analysis | Entity extraction pattern via `parse_json(Entities)` + `mv-expand` documented, entity Type filtering by "account"/"ip"/"host" verified, `summarize count() by EntityType, EntityName` pattern identified |
</phase_requirements>

## Standard Stack

### Core (Phase 2 Only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| azure-monitor-query | 2.0.0 (installed) | `LogsQueryClient` for all KQL queries | Only maintained SDK for querying Log Analytics. v2.0.0 is current major release. |
| azure-identity | 1.25.2 (installed) | `DefaultAzureCredential` for auth | Already configured in Phase 1. Single credential chain. |
| azure-core | 1.38.2 (installed) | `HttpResponseError`, `RetryPolicy`, pipeline policies | Transitive dependency; provides built-in retry and error handling. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses (stdlib) | N/A | Typed result models (Incident, Alert, TrendPoint, etc.) | All query result types. Python 3.14 stdlib. |
| datetime (stdlib) | N/A | Time window calculations, relative timestamp formatting | Every query that involves time ranges. |

### Not Needed in Phase 2

| Library | Why Deferred |
|---------|-------------|
| tenacity / backoff | azure-core's built-in RetryPolicy already handles 429/5xx with exponential backoff |
| requests | Not needed -- all Sentinel access is via KQL through LogsQueryClient, no REST API calls needed for Phase 2 queries |
| pandas | Not needed -- we parse LogsTable rows directly into dataclasses, not DataFrames |

## Architecture Patterns

### Recommended Project Structure (Phase 2 Additions)

```
src/
+-- queries/                    # KQL template registry (per-domain modules)
|   +-- __init__.py             # Exports all templates, builder function
|   +-- incidents.py            # Incident list, incident detail, incident by name
|   +-- alerts.py               # Alert list, alert by severity/time
|   +-- trends.py               # Alert trends over time (summarize/make-series)
|   +-- entities.py             # Top attacked entities (account, IP, host)
+-- models.py                   # Dataclass definitions (Incident, Alert, TrendPoint, Entity, QueryResult, QueryError)
+-- projections.py              # Per-query-type field projection configs
+-- sentinel_client.py          # SentinelClient class wrapping LogsQueryClient
+-- config.py                   # (existing, extend with query defaults)
tests/
+-- test_sentinel_client.py     # Unit tests with mocked LogsQueryClient
+-- test_queries.py             # Template rendering + parameter validation tests
+-- test_models.py              # Dataclass serialization tests
```

### Pattern 1: KQL Template Registry with Named Placeholders

**What:** Each domain module exports a dictionary of template names to KQL strings with `{named}` placeholders. A shared builder function validates parameters, applies defaults, and substitutes safely.

**When to use:** Every KQL query execution.

**Example:**

```python
# src/queries/incidents.py

TEMPLATES = {
    "list_incidents": """
        SecurityIncident
        | where TimeGenerated > ago({time_range})
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | where Severity in ({severity_filter})
        | project IncidentNumber, Title, Severity, Status, CreatedTime,
                  LastModifiedTime, Owner, AlertIds, Description,
                  FirstActivityTime, LastActivityTime
        | order by CreatedTime desc
        | take {limit}
    """,

    "get_incident_by_number": """
        SecurityIncident
        | where IncidentNumber == {incident_number}
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | project IncidentNumber, Title, Severity, Status, Description,
                  CreatedTime, LastModifiedTime, ClosedTime, Owner,
                  AlertIds, Labels, Classification, ClassificationReason,
                  FirstActivityTime, LastActivityTime, IncidentUrl
    """,

    "get_incident_by_name": """
        SecurityIncident
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | where Title contains "{incident_name}"
        | project IncidentNumber, Title, Severity, Status, Description,
                  CreatedTime, LastModifiedTime, ClosedTime, Owner,
                  AlertIds, Labels, Classification, ClassificationReason,
                  FirstActivityTime, LastActivityTime, IncidentUrl
        | take {limit}
    """,
}
```

```python
# src/queries/__init__.py

from src.queries import incidents, alerts, trends, entities

# Merge all templates into a single registry
TEMPLATE_REGISTRY: dict[str, str] = {
    **incidents.TEMPLATES,
    **alerts.TEMPLATES,
    **trends.TEMPLATES,
    **entities.TEMPLATES,
}

# Per-template timeout configuration (seconds)
TEMPLATE_TIMEOUTS: dict[str, int] = {
    "list_incidents": 60,
    "get_incident_by_number": 60,
    "get_incident_by_name": 60,
    "list_alerts": 60,
    "alert_trend": 180,         # aggregation queries need more time
    "top_entities": 180,        # mv-expand + summarize is heavier
}

DEFAULT_TIMEOUT = 60
```

### Pattern 2: Severity Threshold Model

**What:** Convert a minimum severity level into a KQL `in` clause that includes all severities at or above the threshold. Sentinel has exactly four severity levels: Informational < Low < Medium < High. There is NO Critical level.

**When to use:** Every query that filters by severity.

**Example:**

```python
# src/queries/__init__.py

SEVERITY_ORDER = ["Informational", "Low", "Medium", "High"]

def severity_filter(min_severity: str = "Informational") -> str:
    """Return a KQL-safe comma-separated string of severity values
    at or above the given threshold.

    Examples:
        severity_filter("Medium")  -> "'Medium','High'"
        severity_filter("Informational") -> "'Informational','Low','Medium','High'"
    """
    try:
        idx = SEVERITY_ORDER.index(min_severity)
    except ValueError:
        idx = 0  # default to all severities
    included = SEVERITY_ORDER[idx:]
    return ",".join(f"'{s}'" for s in included)
```

### Pattern 3: Metadata Envelope with Query Timing

**What:** Every query result is wrapped in a metadata envelope containing total count, query execution time in milliseconds, and a truncated flag. This enables the LLM to say "Found 47 incidents, showing top 20" and caveat incomplete data.

**When to use:** Every query result returned from `SentinelClient`.

**Example:**

```python
# src/models.py
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any

@dataclass
class QueryMetadata:
    """Metadata envelope for query results."""
    total: int                     # Total rows returned (before any client-side limit)
    query_ms: float                # Query execution time in milliseconds
    truncated: bool                # True if results were capped or partial
    partial_error: str | None = None  # Error message if partial results

@dataclass
class QueryResult:
    """Wrapper for all query responses."""
    metadata: QueryMetadata
    results: list[Any]

    def to_dict(self) -> dict:
        """Serialize for LLM consumption."""
        return {
            "metadata": asdict(self.metadata),
            "results": [
                r.to_dict() if hasattr(r, 'to_dict') else r
                for r in self.results
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
```

### Pattern 4: LogsTable Row Parsing to Dataclasses

**What:** Parse `LogsTable` rows (which are positional arrays keyed by column index) into typed dataclasses using the `columns` list for field mapping.

**When to use:** Every query result processing step.

**Example:**

```python
# Parsing LogsTable into dataclasses
def parse_table_rows(table, row_factory):
    """Convert LogsTable rows into dataclass instances.

    Args:
        table: LogsTable with .columns (list of str) and .rows (list of LogsTableRow)
        row_factory: Callable that accepts a dict and returns a dataclass instance
    """
    results = []
    for row in table.rows:
        # LogsTableRow supports dict-like access via column names
        row_dict = {col: row[col] for col in table.columns}
        results.append(row_factory(row_dict))
    return results
```

**Critical detail:** `LogsTableRow` in azure-monitor-query v2.0.0 supports both index-based (`row[0]`) and column-name-based (`row["ColumnName"]`) access. Use column-name-based access for readability and maintainability.

### Pattern 5: Partial Result Handling

**What:** The `LogsQueryClient.query_workspace()` method returns either `LogsQueryResult` (success) or `LogsQueryPartialResult` (partial). Always check the `.status` attribute. Partial results contain `.partial_data` (list of LogsTable) and `.partial_error` (with `.code` and `.message`).

**When to use:** Every query execution.

**Example:**

```python
from azure.monitor.query import LogsQueryStatus

def _execute_query(self, query: str, timespan, server_timeout: int):
    """Execute a KQL query and return (tables, is_partial, error_msg)."""
    response = self._client.query_workspace(
        workspace_id=self._workspace_id,
        query=query,
        timespan=timespan,
        server_timeout=server_timeout,
        include_statistics=True,
    )

    if response.status == LogsQueryStatus.SUCCESS:
        tables = response.tables
        query_ms = (
            response.statistics.get("query", {}).get("executionTime", 0) * 1000
            if response.statistics else 0
        )
        return tables, False, None, query_ms

    elif response.status == LogsQueryStatus.PARTIAL:
        tables = response.partial_data
        error = response.partial_error
        query_ms = (
            response.statistics.get("query", {}).get("executionTime", 0) * 1000
            if response.statistics else 0
        )
        return tables, True, f"{error.code}: {error.message}", query_ms

    else:
        # FAILURE -- should not happen with query_workspace (it raises), but handle defensively
        return [], False, "Query failed", 0
```

### Pattern 6: Time Window Mapping

**What:** Map predefined window names to `timedelta` values for the `timespan` parameter AND to KQL `ago()` strings for the query itself. Both are needed: `timespan` for server-side filtering and `ago()` for KQL correctness.

**Example:**

```python
from datetime import timedelta

TIME_WINDOWS = {
    "last_1h":  {"timespan": timedelta(hours=1),  "kql_ago": "1h"},
    "last_24h": {"timespan": timedelta(hours=24), "kql_ago": "24h"},
    "last_3d":  {"timespan": timedelta(days=3),   "kql_ago": "3d"},
    "last_7d":  {"timespan": timedelta(days=7),   "kql_ago": "7d"},
    "last_14d": {"timespan": timedelta(days=14),  "kql_ago": "14d"},
    "last_30d": {"timespan": timedelta(days=30),  "kql_ago": "30d"},
}
```

### Anti-Patterns to Avoid

- **Using only `timespan` OR only `ago()` in KQL:** Both are needed. The `timespan` parameter tells the server the time range for query optimization. The `ago()` in KQL is the actual filter. Using only one can cause unexpected results or poor performance. Official docs confirm this is required for optimal query execution.
- **Not deduplicating SecurityIncident rows:** Every modification creates a new log entry. Without `summarize arg_max(LastModifiedTime, *) by IncidentNumber`, you get duplicate incidents at different points in time.
- **Parsing Entities as a simple string:** The `Entities` column in SecurityAlert is a JSON string containing an array of entity objects. It must be parsed with `parse_json()` and expanded with `mv-expand`, not treated as a flat string.
- **Reimplementing retry logic for 429:** The azure-core RetryPolicy already handles 429 with exponential backoff and Retry-After header respect. Adding application-level retry on top creates double-retry behavior. Only add application-level retry for timeout scenarios where the SDK does not retry.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP 429 / 5xx retry | Custom retry loop with sleep | azure-core built-in `RetryPolicy` (3 retries, exponential backoff, respects Retry-After) | Already configured in `LogsQueryClient`. Handles jitter, max delay (60s), and Retry-After header automatically. |
| KQL parameter injection prevention | Regex sanitization of user input | Named placeholder substitution with type validation in builder function | Builder function validates types before substitution. KQL templates use only known placeholders. No freeform user text enters KQL except incident name search (which uses `contains` operator, not injection-vulnerable). |
| LogsTable-to-dict conversion | Manual index-based row parsing | LogsTableRow column-name access (`row["ColumnName"]`) | v2.0.0 `LogsTableRow` supports dict-like access by column name. No need to track column indices manually. |
| Relative timestamp formatting | Custom time-ago function | Python's `datetime` arithmetic + simple formatter | Straightforward calculation: `now - timestamp` gives timedelta, format based on magnitude (seconds/minutes/hours/days). No library needed for this. |
| Query execution timing | `time.time()` wrapper around query calls | `include_statistics=True` on `query_workspace()` | The API returns server-side execution time in `response.statistics["query"]["executionTime"]`. More accurate than client-side timing which includes network latency. |

**Key insight:** The azure-core retry policy handles the hard parts (429 detection, Retry-After parsing, jitter, exponential backoff). Application code should focus on: (1) configuring per-template `server_timeout`, (2) handling `LogsQueryPartialResult`, and (3) wrapping errors in the structured `QueryError` format.

## Common Pitfalls

### Pitfall 1: SecurityIncident Row Duplication

**What goes wrong:** Queries return multiple rows per incident because every modification creates a new log entry.
**Why it happens:** The SecurityIncident table is append-only. Creating, updating severity, changing status, adding comments -- each action appends a new row with the same IncidentNumber but a new TimeGenerated.
**How to avoid:** Always use `summarize arg_max(LastModifiedTime, *) by IncidentNumber` to get the latest state of each incident. This is documented in official Microsoft Sentinel KQL examples.
**Warning signs:** Query returns 500 rows when the workspace only has 50 incidents. Duplicate IncidentNumbers in results.

### Pitfall 2: Severity Column Name Mismatch Between Tables

**What goes wrong:** Queries use `Severity` for both SecurityIncident and SecurityAlert, but SecurityAlert uses `AlertSeverity`.
**Why it happens:** The tables were designed by different teams. The column names are inconsistent.
**How to avoid:** Use `Severity` for SecurityIncident and `AlertSeverity` for SecurityAlert. Define this mapping in the projection config so it's not hardcoded in templates.
**Warning signs:** KQL query returns empty results when filtering alerts by severity. No error -- just zero rows because the column name is wrong.

### Pitfall 3: Entity Extraction Complexity

**What goes wrong:** Developers try to use the `Entities` column directly or parse it as a simple JSON object. The actual structure is a JSON string containing an array of heterogeneous entity objects with different schemas per entity type.
**Why it happens:** The SecurityAlert table documentation is sparse on the Entities column format.
**How to avoid:** Use `parse_json(Entities)` to convert to dynamic, then `mv-expand` to flatten the array, then filter by `Type` field. Each entity type has different properties (Account has `Name`/`AadUserId`, IP has `Address`, Host has `HostName`/`DnsDomain`).
**Warning signs:** Entity queries return one row per alert instead of one row per entity. Or `mv-expand` returns null because `parse_json` was not applied first.

### Pitfall 4: Timespan Parameter vs KQL ago() Mismatch

**What goes wrong:** Setting `timespan=timedelta(days=7)` but using `ago(24h)` in the KQL query. The server restricts to 7 days but the KQL only filters to 24 hours, or vice versa.
**Why it happens:** The relationship between the `timespan` parameter and KQL time filters is confusing. They serve different purposes.
**How to avoid:** Always align them. The `timespan` parameter is a server-side optimization hint. The `ago()` in KQL is the actual filter. Use the `TIME_WINDOWS` mapping to keep them synchronized.
**Warning signs:** Query returns fewer results than expected, or returns results outside the expected time range.

### Pitfall 5: server_timeout Too Low for Aggregation Queries

**What goes wrong:** Trend queries using `summarize ... by bin()` or `make-series` time out with the default 180-second timeout on large workspaces.
**Why it happens:** Aggregation operators scan more data than simple `where + take` queries. The `make-series` operator is particularly expensive because it generates fixed-interval time series with gap filling.
**How to avoid:** Set `server_timeout` per template category: 60s for simple lookups (incident by number, alert list), 180s for aggregation queries (trends, entity rankings). The maximum allowed is 600s (10 minutes).
**Warning signs:** `HttpResponseError` with timeout message. `LogsQueryPartialResult` with partial_error indicating execution time exceeded.

### Pitfall 6: LogsQueryClient Does Not Raise on Partial Results

**What goes wrong:** Developers assume `query_workspace()` raises an exception when results are partial. It does not -- it returns a `LogsQueryPartialResult` silently.
**Why it happens:** The SDK treats partial results as a valid response, not an error. Only complete failures raise exceptions.
**How to avoid:** Always check `response.status`. Handle `LogsQueryStatus.PARTIAL` explicitly by extracting `partial_data` and `partial_error`, and setting the `truncated` flag in the metadata envelope.
**Warning signs:** Results look correct but are silently incomplete. Users get fewer incidents than expected with no error message.

## Code Examples

### Dataclass Models for Query Results

```python
# src/models.py
# Source: Designed based on SecurityIncident and SecurityAlert table schemas
# (https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/securityincident)

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class Incident:
    """Projected fields for incident list and detail views."""
    number: int
    title: str
    severity: str          # "High", "Medium", "Low", "Informational"
    status: str            # "New", "Active", "Closed"
    created_time: datetime
    last_modified_time: datetime
    description: str = ""
    owner: str = ""        # Extracted from Owner dynamic field
    alert_count: int = 0   # len(AlertIds)
    closed_time: datetime | None = None
    first_activity_time: datetime | None = None
    last_activity_time: datetime | None = None
    incident_url: str = ""
    classification: str = ""
    classification_reason: str = ""
    labels: list[str] | None = None
    # Relative time string, computed post-query
    created_time_ago: str = ""
    last_modified_time_ago: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert datetimes to ISO strings for JSON serialization
        for key in ("created_time", "last_modified_time", "closed_time",
                     "first_activity_time", "last_activity_time"):
            val = d.get(key)
            if isinstance(val, datetime):
                d[key] = val.isoformat()
        return d


@dataclass
class Alert:
    """Projected fields for alert list views."""
    name: str              # AlertName
    display_name: str      # DisplayName
    severity: str          # AlertSeverity: "High", "Medium", "Low", "Informational"
    status: str
    time_generated: datetime
    description: str = ""
    tactics: str = ""
    techniques: str = ""
    provider_name: str = ""
    compromised_entity: str = ""
    system_alert_id: str = ""
    # Relative time
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
    severity: str = ""     # Optional grouping dimension

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "count": self.count,
            "severity": self.severity,
        }


@dataclass
class EntityCount:
    """A ranked entity with occurrence count."""
    entity_type: str       # "account", "ip", "host"
    entity_name: str       # The actual value (username, IP address, hostname)
    count: int

    def to_dict(self) -> dict:
        return asdict(self)
```

### Incident-Related Alerts Query (for QUERY-02)

```python
# src/queries/incidents.py
# Source: https://learn.microsoft.com/en-us/azure/sentinel/manage-soc-with-incident-metrics

TEMPLATES = {
    # ... (list_incidents, get_incident_by_number shown above)

    "get_incident_alerts": """
        let incident_alerts = SecurityIncident
            | where IncidentNumber == {incident_number}
            | summarize arg_max(LastModifiedTime, *) by IncidentNumber
            | mv-expand AlertId = AlertIds
            | project tostring(AlertId);
        SecurityAlert
        | where SystemAlertId in (incident_alerts)
        | project AlertName, DisplayName, AlertSeverity, Status,
                  TimeGenerated, Description, Tactics, Techniques,
                  ProviderName, CompromisedEntity, Entities, SystemAlertId
    """,

    "get_incident_entities": """
        let incident_alerts = SecurityIncident
            | where IncidentNumber == {incident_number}
            | summarize arg_max(LastModifiedTime, *) by IncidentNumber
            | mv-expand AlertId = AlertIds
            | project tostring(AlertId);
        SecurityAlert
        | where SystemAlertId in (incident_alerts)
        | extend EntitiesParsed = parse_json(Entities)
        | mv-expand Entity = EntitiesParsed
        | extend EntityType = tostring(Entity.Type),
                 EntityName = case(
                     Entity.Type == "account", tostring(Entity.Name),
                     Entity.Type == "ip", tostring(Entity.Address),
                     Entity.Type == "host", tostring(Entity.HostName),
                     Entity.Type == "url", tostring(Entity.Url),
                     Entity.Type == "file", tostring(Entity.Name),
                     tostring(Entity.Name)
                 )
        | where isnotempty(EntityName)
        | distinct EntityType, EntityName
    """,
}
```

### Alert Trend Query (for QUERY-04)

```python
# src/queries/trends.py
# Source: Pattern based on Microsoft Sentinel SOC metrics workbook

TEMPLATES = {
    "alert_trend": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | summarize Count=count() by bin(TimeGenerated, {bin_size}), AlertSeverity
        | order by TimeGenerated asc
    """,

    "alert_trend_total": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | summarize Count=count() by bin(TimeGenerated, {bin_size})
        | order by TimeGenerated asc
    """,
}
```

### Top Attacked Entities Query (for QUERY-05)

```python
# src/queries/entities.py
# Source: SecurityAlert Entities JSON parsing pattern from
# https://learn.microsoft.com/en-us/azure/sentinel/entities-reference

TEMPLATES = {
    "top_entities": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | extend EntitiesParsed = parse_json(Entities)
        | mv-expand Entity = EntitiesParsed
        | extend EntityType = tostring(Entity.Type),
                 EntityName = case(
                     Entity.Type == "account", tostring(Entity.Name),
                     Entity.Type == "ip", tostring(Entity.Address),
                     Entity.Type == "host", tostring(Entity.HostName),
                     tostring(Entity.Name)
                 )
        | where isnotempty(EntityName)
        | where EntityType in ("account", "ip", "host")
        | summarize AlertCount=count(), Severities=make_set(AlertSeverity)
            by EntityType, EntityName
        | order by AlertCount desc
        | take {limit}
    """,
}
```

### SentinelClient Core Structure

```python
# src/sentinel_client.py (skeleton)
import json
import time
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus

from src.config import Settings
from src.models import (
    Alert, EntityCount, Incident, QueryError, QueryMetadata, QueryResult, TrendPoint,
)
from src.queries import TEMPLATE_REGISTRY, TEMPLATE_TIMEOUTS, DEFAULT_TIMEOUT, TIME_WINDOWS, severity_filter


class SentinelClient:
    """Executes predefined KQL templates against a Sentinel workspace."""

    def __init__(self, settings: Settings):
        self._workspace_id = settings.sentinel_workspace_id
        credential = DefaultAzureCredential()
        self._client = LogsQueryClient(credential)

    def query_incidents(
        self,
        time_window: str = "last_24h",
        min_severity: str = "Informational",
        limit: int = 20,
    ) -> QueryResult | QueryError:
        """Query security incidents filtered by severity and time range."""
        ...

    def get_incident_detail(
        self,
        incident_ref: int | str,
    ) -> QueryResult | QueryError:
        """Get detailed incident info by number or name, including alerts and entities."""
        ...

    def query_alerts(
        self,
        time_window: str = "last_24h",
        min_severity: str = "Informational",
        limit: int = 20,
    ) -> QueryResult | QueryError:
        """Query security alerts filtered by severity and time range."""
        ...

    def get_alert_trend(
        self,
        time_window: str = "last_7d",
        min_severity: str = "Informational",
    ) -> QueryResult | QueryError:
        """Get alert trend data over a configurable time period."""
        ...

    def get_top_entities(
        self,
        time_window: str = "last_7d",
        min_severity: str = "Informational",
        limit: int = 10,
    ) -> QueryResult | QueryError:
        """Get most-targeted entities ranked by alert count."""
        ...
```

### Relative Time Formatting

```python
# src/models.py (or a utility module)

from datetime import datetime, timezone

def format_relative_time(dt: datetime) -> str:
    """Format a datetime as a human-readable relative string.

    Examples: '2 hours ago', 'yesterday at 3:14 PM', '5 days ago'
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt

    seconds = int(delta.total_seconds())
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 172800:  # 2 days
        return f"yesterday at {dt.strftime('%-I:%M %p')}"
    elif seconds < 604800:  # 7 days
        days = seconds // 86400
        return f"{days} days ago"
    else:
        return dt.strftime("%b %d, %Y")
```

## Discretionary Recommendations

For areas marked as Claude's discretion in the CONTEXT.md:

### Time Window Set

Recommended predefined windows: `last_1h`, `last_24h`, `last_3d`, `last_7d`, `last_14d`, `last_30d`. Rationale: `last_3d` and `last_14d` fill natural gaps between 24h/7d and 7d/30d. SOC analysts commonly look at "last few days" and "last two weeks" patterns.

### Default and Max Result Limits

| Query Type | Default Limit | Hard Cap | Rationale |
|-----------|--------------|----------|-----------|
| Incident list | 20 | 100 | 20 fits in one terminal screen; 100 is more than enough for LLM context |
| Alert list | 20 | 100 | Same reasoning as incidents |
| Incident detail alerts | 50 | 200 | An incident rarely has > 50 alerts |
| Alert trend | No limit (one row per time bin) | 365 | Max 365 daily bins |
| Top entities | 10 | 50 | Top 10 is standard ranking; 50 for deep analysis |

### Dataclass Field Names

Use snake_case for all Python field names (PEP 8). Map from PascalCase Sentinel columns in the parser. Example: `IncidentNumber` -> `number`, `AlertSeverity` -> `severity`, `TimeGenerated` -> `time_generated`.

### Backoff Timing and Jitter

**Recommendation: Rely on azure-core's built-in retry policy.** The installed azure-core v1.38.2 defaults are: 3 retries, exponential backoff starting at 0.8s, max 60s delay, retries on [408, 429, 500, 502, 503, 504], respects Retry-After headers. This matches the user's "3 retries with exponential backoff" requirement. The exact timings (0.8s, 1.6s, 3.2s) are close enough to the requested (1s, 2s, 4s) that customization is not needed. If the user wants exact (1s, 2s, 4s) timings, pass `retry_backoff_factor=1.0` when constructing the `LogsQueryClient`.

### Incident Name Matching

**Recommendation: Use `contains` (case-insensitive substring match).** This is the simplest approach that covers most use cases. If the user says "show me the phishing incident," `where Title contains "phishing"` will match "Suspicious Phishing Email Detected." KQL's `contains` operator is case-insensitive by default. Fuzzy matching would require `has_any` or custom logic, which is overkill for a POC.

### Projection Config Format and Location

**Recommendation:** Define projections as dictionaries in `src/projections.py`, keyed by view name (e.g., "incident_list", "incident_detail", "alert_list"). Each value is a list of field names to include from the full row. This allows templates to use `project *` (or a broad projection) and have the Python layer filter fields post-query.

```python
# src/projections.py
PROJECTIONS = {
    "incident_list": [
        "number", "title", "severity", "status",
        "created_time", "alert_count", "last_modified_time",
    ],
    "incident_detail": [
        "number", "title", "severity", "status", "description",
        "created_time", "last_modified_time", "closed_time",
        "owner", "alert_count", "labels",
        "classification", "classification_reason",
        "first_activity_time", "last_activity_time", "incident_url",
    ],
    "alert_list": [
        "name", "display_name", "severity", "status",
        "time_generated", "tactics", "provider_name", "compromised_entity",
    ],
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `azure-mgmt-securityinsight` v1.0.0 | `azure-monitor-query` v2.0.0 | Jul 2025 | Old package stale since Jul 2022. New package provides full KQL access to all Sentinel tables. |
| `MetricsClient` in azure-monitor-query | Removed in v2.0.0, moved to separate `azure-monitor-querymetrics` | Jul 2025 | v2.0.0 is Logs-only. Metrics moved to separate package. |
| Manual retry loops for Azure SDK | Built-in `RetryPolicy` in azure-core | Ongoing | Default retry handles 429/5xx with exponential backoff. No custom retry needed for most cases. |
| `query_workspace()` returns raw tables | `LogsTableRow` supports column-name access | v2.0.0 | No need for index-based row access. `row["ColumnName"]` works directly. |

## Open Questions

1. **SecurityIncident.Status valid values**
   - What we know: "New", "Active", "Closed" are used in official KQL examples. These appear to be the standard values.
   - What's unclear: Whether additional status values exist (e.g., "Resolved", "Dismissed"). The official schema documentation does not enumerate valid values.
   - Recommendation: Use "New", "Active", "Closed" as the known values. If other values appear in query results, handle them gracefully (don't crash).

2. **Entity Type identifiers in SecurityAlert.Entities**
   - What we know: Common types include "account", "ip", "host", "url", "file". The `Type` field in the entity JSON uses lowercase strings.
   - What's unclear: The exact list of all possible entity types. Microsoft documentation lists many entity types (mailbox, cloud-application, dns, registry-key, etc.).
   - Recommendation: Focus on the three types the user cares about (account, ip, host) for QUERY-05. Handle unknown types gracefully with a fallback `tostring(Entity.Name)`.

3. **Sentinel Training Lab data quality for entity queries**
   - What we know: Training Lab provides sample incidents and alerts. It is unclear how rich the entity data is in these samples.
   - What's unclear: Whether entity extraction queries will return meaningful results against training lab data, or if the Entities column is empty/sparse in sample data.
   - Recommendation: Build the queries correctly and test against live data. If training lab data lacks entities, note this as a known limitation and verify with real data when available.

## Sources

### Primary (HIGH confidence)
- [Azure Monitor Logs reference - SecurityIncident](https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/securityincident) - Updated 2026-01-27. Complete table schema with all column names, types, and descriptions. Confirmed Severity values: High, Medium, Low, Informational.
- [Azure Monitor Logs reference - SecurityAlert](https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/securityalert) - Updated 2026-01-27. Complete table schema. Confirmed severity column is `AlertSeverity` (not `Severity`).
- [Azure Monitor Query client library for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme?view=azure-python) - Updated 2025-07-30. Official SDK documentation covering LogsQueryClient, query_workspace, query_batch, LogsQueryResult, LogsQueryPartialResult, server_timeout, include_statistics.
- [Azure Monitor service limits](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/service-limits) - Updated 2026-01-19. Confirmed: 5 concurrent queries per user, 200 requests/30s, 3-minute queue timeout, 500K max rows, ~100MB max data, 10-minute max query time.
- [HTTP pipeline and retries in Azure SDK for Python](https://learn.microsoft.com/en-us/azure/developer/python/sdk/fundamentals/http-pipeline-retries) - Updated 2025-07-16. Confirmed: default 3 retries, exponential backoff (0.8s base, 60s max), retries on [408, 429, 500, 502, 503, 504], respects Retry-After.
- [Manage your SOC with incident metrics](https://learn.microsoft.com/en-us/azure/sentinel/manage-soc-with-incident-metrics) - Official KQL examples for SecurityIncident queries, including `summarize arg_max()` deduplication pattern, severity filtering, status filtering.
- Installed SDK inspection (azure-monitor-query 2.0.0, azure-core 1.38.2) - Verified: `LogsQueryClient.query_workspace()` signature, `LogsTable` structure (name, rows, columns, columns_types), `LogsTableRow` column-name access, `HttpResponseError` attributes.

### Secondary (MEDIUM confidence)
- [Microsoft Sentinel entity types reference](https://learn.microsoft.com/en-us/azure/sentinel/entities-reference) - Entity type identifiers and their properties (Account.Name, IP.Address, Host.HostName).
- [make-series vs summarize](https://www.cloudsma.com/2021/04/kusto-make-series-vs-summarize/) - Community article comparing KQL time series approaches. Confirmed make-series provides gap-filling that summarize does not.
- [KQL Sentinel Queries (GitHub)](https://github.com/reprise99/Sentinel-Queries) - Community KQL query patterns for entity extraction from SecurityAlert.

### Tertiary (LOW confidence)
- SecurityIncident Status values -- only "New", "Active", "Closed" confirmed in examples; other values may exist but are not documented.
- Entity Type field casing -- appears to be lowercase in examples but may vary by provider. Needs validation against live data.

## Metadata

**Confidence breakdown:**
- SecurityIncident/SecurityAlert table schemas: HIGH -- verified against official Azure Monitor reference docs (updated 2026-01-27)
- azure-monitor-query SDK API: HIGH -- verified by inspecting installed v2.0.0 package and official docs
- Retry/backoff behavior: HIGH -- verified against azure-core docs and installed v1.38.2 code
- KQL query patterns: HIGH -- based on official Microsoft Sentinel SOC metrics examples
- Entity extraction patterns: MEDIUM -- based on community examples and entity reference docs; needs validation against live data
- Training lab data quality for entities: LOW -- untested assumption that training lab provides entity data

**Research date:** 2026-02-18
**Valid until:** 2026-03-20 (30 days -- Azure SDK APIs are stable; KQL table schemas rarely change)
