---
phase: 02-sentinel-data-access
plan: 01
subsystem: api
tags: [kql, sentinel, azure-monitor-query, dataclass, query-templates]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: Settings dataclass, config module, azure-monitor-query SDK installed
provides:
  - Incident/Alert/TrendPoint/EntityCount dataclasses with serialization
  - QueryResult/QueryError metadata envelope wrappers
  - KQL template registry with 6 templates (incidents + alerts)
  - severity_filter() threshold model and TIME_WINDOWS
  - SentinelClient with query_incidents, get_incident_detail, query_alerts methods
  - Field projection configs for incident_list, incident_detail, alert_list views
  - format_relative_time() utility for human-readable timestamps
affects: [02-sentinel-data-access, 03-ai-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns: [metadata-envelope, kql-template-registry, severity-threshold, post-query-projection, test-injection-via-constructor]

key-files:
  created:
    - src/models.py
    - src/queries/__init__.py
    - src/queries/incidents.py
    - src/queries/alerts.py
    - src/projections.py
    - src/sentinel_client.py
    - tests/test_models.py
    - tests/test_queries.py
    - tests/test_sentinel_client.py
  modified: []

key-decisions:
  - "entity_count defaults to 0 in list view (no cross-table join); populated from entity sub-query in detail view"
  - "Used datetime.UTC alias (Python 3.11+) instead of timezone.utc per ruff UP017"
  - "SentinelClient accepts optional client parameter for test injection (no mocking of constructors needed)"
  - "Severity threshold model: Informational < Low < Medium < High (no Critical in Sentinel)"
  - "get_incident_detail uses 30-day time window for lookups to find older incidents"

patterns-established:
  - "Metadata envelope: every query result wrapped in QueryResult(metadata=QueryMetadata(...), results=[...])"
  - "KQL template registry: per-domain modules with TEMPLATES dicts merged into TEMPLATE_REGISTRY"
  - "build_query() validates template name and required placeholders before rendering"
  - "Post-query projection: templates return full rows, Python applies field filtering via apply_projection()"
  - "Test injection: SentinelClient(settings, client=mock_client) for unit testing without live Azure"

requirements-completed: [QUERY-01, QUERY-02, QUERY-03]

# Metrics
duration: 9min
completed: 2026-02-19
---

# Phase 2 Plan 01: Sentinel Data Access - Models, Templates, and Client Summary

**Incident/alert query pipeline with KQL template registry, typed dataclass results, metadata envelopes, and SentinelClient with 3 query methods plus 67 passing tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-02-19T00:21:21Z
- **Completed:** 2026-02-19T00:29:53Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Complete data model layer: Incident (with entity_count), Alert, TrendPoint, EntityCount, QueryResult, QueryError dataclasses with to_dict() serialization
- KQL template registry with 6 templates covering incident list/detail/name-search, incident alerts/entities, and alert list
- SentinelClient wrapping LogsQueryClient with query_incidents(), get_incident_detail(), and query_alerts() methods
- Severity threshold filtering, time window mapping, result limit clamping, partial result handling, and structured error returns
- 56 new tests (43 model/query + 13 client) all passing with zero ruff lint errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create data models, KQL template registry, and projection configs** - `d34c529` (feat)
2. **Task 2: Implement SentinelClient with incident and alert query methods** - `db6f00d` (feat)

## Files Created/Modified
- `src/models.py` - Incident, Alert, TrendPoint, EntityCount, QueryMetadata, QueryResult, QueryError dataclasses + format_relative_time()
- `src/queries/__init__.py` - TEMPLATE_REGISTRY, severity_filter(), build_query(), TIME_WINDOWS, DEFAULT_LIMITS, MAX_LIMITS, TEMPLATE_TIMEOUTS
- `src/queries/incidents.py` - 5 KQL templates: list_incidents, get_incident_by_number/name, get_incident_alerts/entities
- `src/queries/alerts.py` - 1 KQL template: list_alerts (uses AlertSeverity, not Severity)
- `src/projections.py` - PROJECTIONS dict with incident_list, incident_detail, alert_list views + apply_projection() helper
- `src/sentinel_client.py` - SentinelClient class with _execute_query, _parse_incidents/alerts/entities, query_incidents, get_incident_detail, query_alerts
- `tests/test_models.py` - 21 tests for dataclass serialization and format_relative_time
- `tests/test_queries.py` - 22 tests for severity_filter, TIME_WINDOWS, TEMPLATE_REGISTRY, build_query, limits
- `tests/test_sentinel_client.py` - 13 tests with mocked LogsQueryClient for all query methods and error handling

## Decisions Made
- entity_count field on Incident defaults to 0 in list view (SecurityIncident has no entity data natively); populated from entity sub-query in get_incident_detail()
- SentinelClient accepts optional `client` parameter for test injection, avoiding need to mock DefaultAzureCredential in unit tests
- Used datetime.UTC alias (Python 3.11+) throughout per ruff UP017 rule
- get_incident_detail() uses a 30-day time window for lookups so it can find older incidents by number or name
- Labels parsed from Sentinel's JSON format (array of {labelName: str} objects) into simple string lists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed naive datetime test using local time instead of UTC**
- **Found during:** Task 1 (test_models.py verification)
- **Issue:** Test created naive datetime with `datetime.now()` (local time) but format_relative_time compares against UTC, causing 8-hour offset on non-UTC systems
- **Fix:** Changed test to use `datetime.now(timezone.utc).replace(tzinfo=None)` to create a naive datetime that is actually 5 minutes ago in UTC
- **Files modified:** tests/test_models.py
- **Verification:** Test passes on all timezones
- **Committed in:** d34c529 (part of Task 1 commit)

**2. [Rule 3 - Blocking] Fixed missing LogsQueryClient import in test file**
- **Found during:** Task 2 (test_sentinel_client.py initial run)
- **Issue:** Test fixture referenced `LogsQueryClient` for mock spec but import was missing (only `LogsQueryStatus` was imported)
- **Fix:** Added `LogsQueryClient` to the import statement
- **Files modified:** tests/test_sentinel_client.py
- **Verification:** All 13 tests pass
- **Committed in:** db6f00d (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes were minor and necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the two auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SentinelClient ready for Plan 02 extension with trend/entity query methods
- TEMPLATE_REGISTRY designed to merge additional domain modules (trends.py, entities.py)
- Projection configs ready for alert_trend and top_entities views
- 67 total tests pass (11 config + 21 model + 22 query + 13 client)

## Self-Check: PASSED

- All 9 created files exist on disk
- Commit d34c529 (Task 1) verified in git log
- Commit db6f00d (Task 2) verified in git log
- 67/67 tests passing
- ruff check: All checks passed

---
*Phase: 02-sentinel-data-access*
*Completed: 2026-02-19*
