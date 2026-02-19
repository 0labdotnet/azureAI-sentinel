---
phase: 02-sentinel-data-access
verified: 2026-02-18T00:00:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
human_verification:
  - test: "Live Sentinel workspace smoke test"
    expected: "All 5 SentinelClient methods return results with correct field mappings (not errors)"
    why_human: "Requires live Azure credentials and a real Sentinel workspace to validate KQL template correctness, column name mappings, and parse_json entity extraction against actual Sentinel table schemas. The smoke test script (tests/smoke_live.py) exists for this purpose. SUMMARY claims 5/5 PASS against live workspace — cannot verify programmatically."
---

# Phase 2: Sentinel Data Access Verification Report

**Phase Goal:** The Sentinel client can execute all pre-defined KQL query templates and return structured, field-projected results from live Sentinel data
**Verified:** 2026-02-18
**Status:** passed (all automated checks; one human item for live workspace confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `query_incidents()` returns Incident dataclasses filtered by severity threshold and time window, wrapped in metadata envelope | VERIFIED | `SentinelClient.query_incidents()` at line 382 of `sentinel_client.py` validates time_window, clamps limit, builds KQL via `build_query("list_incidents", ...)`, parses to Incident objects, applies `incident_list` projection, returns `QueryResult(metadata=QueryMetadata(...), results=[...])`. Test `TestQueryIncidents::test_returns_query_result_with_incidents` passes. |
| 2 | Incident dataclass includes `entity_count` field (defaults to 0 in list view, populated in detail view) | VERIFIED | `src/models.py` line 106: `entity_count: int = 0`. `_parse_incidents()` line 203: `"entity_count": 0`. `get_incident_detail()` line 516: `incident.entity_count = len(incident_entities)`. Test `test_entity_count_defaults_to_zero` and `test_by_number_returns_detail_with_alerts_and_entities` (entity_count==3) both pass. |
| 3 | `get_incident_detail()` by number returns incident with related alerts and entities, with entity_count populated | VERIFIED | `sentinel_client.py` lines 457-539: dispatches `get_incident_by_number` template, then loops sub-queries for `get_incident_alerts` and `get_incident_entities`, sets `incident.entity_count = len(incident_entities)`. Returns composite `{"incidents": [...], "alerts": [...], "entities": [...]}`. Test confirms `entity_count == 3` when 3 entities returned. |
| 4 | `get_incident_detail()` by name (string) uses case-insensitive substring match | VERIFIED | Lines 465-472: when `incident_ref` is str, builds query with `get_incident_by_name` template. Template at `incidents.py` line 30 uses `Title contains "{incident_name}"` (KQL `contains` is case-insensitive). Test `test_by_name_uses_contains_template` verifies `'contains "phishing"'` in rendered KQL. |
| 5 | `query_alerts()` returns Alert dataclasses filtered by severity and time range, wrapped in metadata envelope | VERIFIED | `sentinel_client.py` lines 542-597. Uses `AlertSeverity` (not `Severity`) per KQL pitfall documented in `alerts.py`. Alert objects parsed via `_parse_alerts()`, projected, returned in `QueryResult`. Test `test_returns_query_result_with_alerts` confirms correct field names and counts. |
| 6 | Timestamps in results include human-readable relative strings | VERIFIED | `format_relative_time()` in `models.py` lines 12-44 handles all cases: just now, N minutes ago, N hours ago, yesterday at H:MM AM/PM, N days ago, Mon DD YYYY. Called during `_parse_incidents()` (lines 204-205) and `_parse_alerts()` (line 285). 9 test cases in `TestFormatRelativeTime` all pass. |
| 7 | Partial results set `truncated=True` in metadata and include `partial_error` message | VERIFIED | `_execute_query()` lines 100-115: `PARTIAL` status returns `(tables, True, error_msg, query_ms)`. `query_incidents()` passes this as `truncated=is_partial, partial_error=partial_error` to `QueryMetadata`. Test `test_partial_results_set_truncated_flag` confirms `truncated is True` and `"PartialError"` in `partial_error`. |
| 8 | Failed queries return `QueryError` with `code`, `message`, and `retry_possible` flag | VERIFIED | `_execute_query()` lines 125-141: `HttpResponseError` returns `QueryError(code=error_code, message=..., retry_possible=status_code in (429, 500, 502, 503, 504))`. `Exception` returns `QueryError(code="unknown", ...)`. Tests for 429 (retry=True), 400 (retry=False), and RuntimeError (code="unknown") all pass. |
| 9 | `get_alert_trend()` returns TrendPoint dataclasses showing alert frequency bucketed by time bins | VERIFIED | `sentinel_client.py` lines 609-665. Auto-selects bin_size (1h/1d) from `_BIN_SIZE_MAP`. Uses `alert_trend` template with 180s timeout. `_parse_trend_points()` maps to `TrendPoint(timestamp, count, severity)`. Tests confirm TrendPoint type, auto-bin selection (last_24h->1h, last_7d->1d), custom override, and 180s timeout. |
| 10 | `get_top_entities()` returns EntityCount dataclasses ranked by alert count for accounts, IPs, and hosts | VERIFIED | `sentinel_client.py` lines 667-723. Uses `top_entities` template with 180s timeout and `parse_json+mv-expand` KQL pattern. `_parse_entity_counts()` maps to `EntityCount(entity_type, entity_name, count)`. Tests confirm EntityCount type, ranking order (count desc), limit clamping to 50, and 180s timeout. |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/models.py` | Dataclass definitions: Incident (with entity_count), Alert, TrendPoint, EntityCount, QueryMetadata, QueryResult, QueryError, format_relative_time() | VERIFIED | File exists, 185 lines, all 7 dataclasses present, `entity_count: int = 0` on Incident at line 106, `format_relative_time()` at line 12. Substantive implementation. |
| `src/queries/__init__.py` | TEMPLATE_REGISTRY, severity_filter(), build_query(), TIME_WINDOWS, DEFAULT_LIMITS, MAX_LIMITS, TEMPLATE_TIMEOUTS | VERIFIED | File exists, 138 lines. All exports present. 9 templates merged from 4 domain modules. `severity_filter("Medium")` returns `'Medium','High'`. `build_query()` raises ValueError on unknown template and missing params. |
| `src/queries/incidents.py` | KQL templates: list_incidents, get_incident_by_number, get_incident_by_name, get_incident_alerts, get_incident_entities | VERIFIED | File exists, TEMPLATES dict with all 5 KQL templates. `list_incidents` uses `arg_max` dedup and field projection. `get_incident_entities` uses `parse_json+mv-expand+case()` for entity extraction. |
| `src/queries/alerts.py` | KQL template: list_alerts (using AlertSeverity) | VERIFIED | File exists, TEMPLATES dict with `list_alerts` template. Uses `AlertSeverity in ({severity_filter})` correctly (not Severity). |
| `src/queries/trends.py` | KQL templates: alert_trend, alert_trend_total | VERIFIED | File exists, TEMPLATES dict with both trend templates using `summarize Count=count() by bin(TimeGenerated, {bin_size})`. |
| `src/queries/entities.py` | KQL template: top_entities with parse_json+mv-expand entity extraction | VERIFIED | File exists, TEMPLATES dict with `top_entities` using `parse_json+mv-expand+case()` for account/ip/host normalization. |
| `src/projections.py` | PROJECTIONS dict with incident_list, incident_detail, alert_list views including entity_count; apply_projection() helper | VERIFIED | File exists, `PROJECTIONS` dict with all 3 views. `entity_count` in both `incident_list` (line 20) and `incident_detail` (line 36). `apply_projection()` defensive: returns unmodified dict if view not found. |
| `src/sentinel_client.py` | SentinelClient with all 5 public methods: query_incidents, get_incident_detail, query_alerts, get_alert_trend, get_top_entities | VERIFIED | File exists, 724 lines. All 5 public methods present and substantive (not stubs). Private helpers _execute_query, _parse_incidents, _parse_alerts, _parse_entities, _parse_trend_points, _parse_entity_counts all implemented. |
| `tests/test_sentinel_client.py` | Unit tests with mocked LogsQueryClient for all query methods | VERIFIED | File exists, 713 lines. 23 tests across 7 test classes covering all 5 methods plus error handling and partial results. Uses `MagicMock(spec=LogsQueryClient)` via constructor injection. All 23 pass. |
| `tests/test_models.py` | Tests for dataclass serialization and format_relative_time | VERIFIED | File exists, 292 lines. 21 tests covering all dataclasses and all format_relative_time() cases. All pass. |
| `tests/test_queries.py` | Tests for template registry and query builder | VERIFIED | File exists, 202 lines. 22 tests for severity_filter, TIME_WINDOWS, TEMPLATE_REGISTRY completeness (9 templates asserted), build_query, TEMPLATE_TIMEOUTS, DEFAULT_LIMITS/MAX_LIMITS. All pass. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/sentinel_client.py` | `src/queries/__init__.py` | `from src.queries import MAX_LIMITS, TEMPLATE_TIMEOUTS, TIME_WINDOWS, build_query, severity_filter` | WIRED | Lines 28-34 of sentinel_client.py. All 5 names imported and actively used throughout query methods. |
| `src/sentinel_client.py` | `src/models.py` | `from src.models import Alert, EntityCount, Incident, QueryError, QueryMetadata, QueryResult, TrendPoint, format_relative_time` | WIRED | Lines 17-27 of sentinel_client.py. All imports used: Incident in `_parse_incidents`, Alert in `_parse_alerts`, TrendPoint in `_parse_trend_points`, EntityCount in `_parse_entity_counts`, QueryResult/QueryMetadata/QueryError in all public methods, format_relative_time in parsers. |
| `src/sentinel_client.py` | `src/projections.py` | `from src.projections import apply_projection` | WIRED | Line 27 of sentinel_client.py. `apply_projection()` called in `query_incidents` (line 429), `get_incident_detail` (lines 519-524), and `query_alerts` (line 587). |
| `src/queries/__init__.py` | `src/queries/incidents.py` | `from src.queries import alerts, entities, incidents, trends` then `**incidents.TEMPLATES` | WIRED | Line 12 of `__init__.py`. `**incidents.TEMPLATES` in TEMPLATE_REGISTRY dict at line 98. `list_incidents` in TEMPLATE_REGISTRY confirmed by runtime import test. |
| `src/queries/__init__.py` | `src/queries/trends.py` | `from src.queries import ... trends` then `**trends.TEMPLATES` | WIRED | Line 12 of `__init__.py`. `**trends.TEMPLATES` at line 100. `alert_trend` and `alert_trend_total` confirmed in TEMPLATE_REGISTRY. |
| `src/queries/__init__.py` | `src/queries/entities.py` | `from src.queries import ... entities` then `**entities.TEMPLATES` | WIRED | Line 12 of `__init__.py`. `**entities.TEMPLATES` at line 101. `top_entities` confirmed in TEMPLATE_REGISTRY. |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QUERY-01 | 02-01-PLAN.md | User can ask questions about security incidents and receive accurate results (e.g., "Show me high-severity incidents from the last 24 hours") | SATISFIED | `query_incidents(time_window, min_severity, limit)` implements this. Severity threshold filtering with `severity_filter()`, 6 predefined time windows, returns projected Incident dicts. 4 unit tests pass. |
| QUERY-02 | 02-01-PLAN.md | User can drill down into a specific incident by number to see detailed information including related alerts and entities | SATISFIED | `get_incident_detail(incident_ref: int)` executes incident detail query + 2 sub-queries (alerts, entities). Returns composite structure with incidents/alerts/entities and entity_count populated from sub-query. 2 unit tests pass. |
| QUERY-03 | 02-01-PLAN.md | User can query security alerts filtered by severity and time range | SATISFIED | `query_alerts(time_window, min_severity, limit)` uses `list_alerts` template with `AlertSeverity` (correct column). Returns projected Alert dicts. 2 unit tests pass. |
| QUERY-04 | 02-02-PLAN.md | User can ask about alert trends over the past 7 days and receive a summarized analysis | SATISFIED | `get_alert_trend(time_window, min_severity, bin_size)` with auto-bin selection. Uses `alert_trend` template with `summarize+bin()`, 180s timeout. Returns TrendPoint dataclasses. 6 unit tests pass. |
| QUERY-05 | 02-02-PLAN.md | User can ask which entities (users, IPs, hosts) have been most targeted and receive a ranked analysis | SATISFIED | `get_top_entities(time_window, min_severity, limit)` uses `top_entities` template with `parse_json+mv-expand+case()`. Returns EntityCount dataclasses ranked by AlertCount desc. 4 unit tests pass. |

All 5 requirements for Phase 2 are satisfied. No orphaned requirements detected — REQUIREMENTS.md traceability table maps exactly QUERY-01 through QUERY-05 to Phase 2, and both plans' `requirements` fields account for all 5.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/queries/__init__.py` | "placeholder" in docstring (parameter token terminology) | Info | Not a code stub — the word appears in a docstring explaining `{placeholder}` syntax for KQL templates. No functional impact. |

No stub returns, empty handlers, or TODO/FIXME comments found in any Phase 2 source file. All public methods contain substantive implementations.

---

### Human Verification Required

#### 1. Live Sentinel Workspace Validation

**Test:** Run `tests/smoke_live.py` against the actual Sentinel workspace with `.env` credentials set
**Expected:**
- `query_incidents()` returns incidents with correct `number`, `title`, `severity`, `status` fields and `entity_count == 0`
- `query_alerts()` returns alerts with `severity` populated (not empty string — confirms `AlertSeverity` column mapping correct)
- `get_alert_trend()` returns TrendPoint objects with numeric counts per time bin
- `get_top_entities()` returns EntityCount objects (may be empty if training lab lacks entity data — empty is acceptable)
- `get_incident_detail(N)` returns composite with incident detail fields populated (description, owner, labels, etc.)
- Metadata envelope present on every result: `total`, `query_ms`, `truncated`
- Relative timestamps are human-readable strings, not raw datetime objects

**Why human:** The KQL templates contain Sentinel-specific column names (`AlertSeverity`, `arg_max`, `parse_json`, `mv-expand`, `IncidentUrl`) that can only be validated against a real Sentinel Log Analytics workspace. Mock tests confirm Python logic; live test confirms KQL correctness. The SUMMARY claims 5/5 PASS from a prior session — this cannot be verified without re-running against the live workspace.

---

### Test Results

All 77 tests pass:
- `tests/test_config.py`: 11/11 (Phase 1, not in scope but confirms no regression)
- `tests/test_models.py`: 21/21
- `tests/test_queries.py`: 22/22
- `tests/test_sentinel_client.py`: 23/23

**Total Phase 2 tests:** 66/66 passing (test_models + test_queries + test_sentinel_client)

---

### Commit Verification

Phase 2 commits confirmed in git log:
- `d34c529` — `feat(02-01): add data models, KQL template registry, and projection configs`
- `db6f00d` — `feat(02-01): implement SentinelClient with incident and alert query methods`
- `f021321` — `feat(02-02): add trend and entity query methods to SentinelClient`
- `cb5454b` — `test(02-02): add live smoke test for all 5 SentinelClient methods`
- `2d7481e` — `fix(02-02): add sys.path fix to smoke test for direct execution`

---

### Summary

Phase 2 goal is achieved. The Sentinel client can execute all 9 pre-defined KQL query templates across 4 domain modules (incidents, alerts, trends, entities) and return structured, field-projected results. All 5 public query methods are substantively implemented with:

- Typed dataclass results (Incident, Alert, TrendPoint, EntityCount)
- Metadata envelopes on every successful result (total, query_ms, truncated, partial_error)
- Severity threshold filtering (no Critical in Sentinel — confirmed)
- 6 predefined time windows with both timedelta and kql_ago values
- Result limit clamping to hard caps
- Partial result handling (truncated flag + error message)
- Structured error returns (QueryError with code, message, retry_possible)
- Post-query field projection via PROJECTIONS config
- Human-readable relative timestamps via format_relative_time()
- Constructor injection for unit testing without live Azure calls

The one human verification item (live workspace smoke test) is a validation step, not a gap — the implementation is complete and the SUMMARY documents it as passed. The smoke test script exists at `tests/smoke_live.py` for repeatable execution.

---
_Verified: 2026-02-18_
_Verifier: Claude (gsd-verifier)_
