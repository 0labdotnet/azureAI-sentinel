---
phase: 02-sentinel-data-access
plan: 02
subsystem: api
tags: [kql, sentinel, trend-analysis, entity-ranking, aggregation, live-verification]

# Dependency graph
requires:
  - phase: 02-sentinel-data-access
    plan: 01
    provides: SentinelClient with incident/alert queries, KQL template registry, data models, severity threshold filtering
provides:
  - get_alert_trend() method returning TrendPoint dataclasses bucketed by configurable time bins
  - get_top_entities() method returning EntityCount dataclasses ranked by alert count
  - KQL templates for alert_trend, alert_trend_total, and top_entities with 180s aggregation timeout
  - Live-verified data access layer with all 5 query methods confirmed against real Sentinel workspace
  - Complete Phase 2 Sentinel data access layer ready for Phase 3 AI orchestration
affects: [03-ai-orchestration]

# Tech tracking
tech-stack:
  added: []
  patterns: [aggregation-timeout-180s, auto-bin-size-selection, parse-json-mv-expand-entity-extraction]

key-files:
  created:
    - src/queries/trends.py
    - src/queries/entities.py
    - tests/smoke_live.py
  modified:
    - src/queries/__init__.py
    - src/sentinel_client.py
    - tests/test_sentinel_client.py

key-decisions:
  - "Aggregation queries (trend, entity) use 180s server_timeout vs 60s for simple queries"
  - "Auto-select bin_size: 1h for short windows (last_1h/last_24h), 1d for longer (last_3d+)"
  - "Entity extraction uses parse_json + mv-expand KQL pattern with case() for account/ip/host types"

patterns-established:
  - "Aggregation timeout: heavier KQL operators (summarize+bin, parse_json+mv-expand) get 180s vs default 60s"
  - "Auto-bin selection: method infers granularity from time window when caller does not specify"
  - "Live smoke test: tests/smoke_live.py exercises all client methods against real workspace for end-to-end validation"

requirements-completed: [QUERY-04, QUERY-05]

# Metrics
duration: 18min
completed: 2026-02-18
---

# Phase 2 Plan 02: Trend/Entity Queries and Live Data Verification Summary

**Alert trend and entity ranking queries with auto-bin selection, 180s aggregation timeout, and live verification of all 5 SentinelClient methods against real Sentinel workspace**

## Performance

- **Duration:** 18 min (across two sessions with human-verify checkpoint)
- **Started:** 2026-02-18
- **Completed:** 2026-02-18
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Two new KQL template modules: trends.py (alert_trend, alert_trend_total) and entities.py (top_entities) with 180s aggregation timeout
- SentinelClient extended with get_alert_trend() (auto-bin selection) and get_top_entities() (parse_json + mv-expand entity extraction)
- All 5 query methods (query_incidents, get_incident_detail, query_alerts, get_alert_trend, get_top_entities) verified against live Sentinel workspace -- 5/5 PASS
- Template registry grown from 6 to 9 templates across 4 domain modules (incidents, alerts, trends, entities)
- Live smoke test script (tests/smoke_live.py) for repeatable end-to-end validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add trend and entity query templates, SentinelClient methods, and unit tests** - `f021321` (feat)
2. **Task 2: Verify all query methods against live Sentinel data** - `cb5454b` (test) + `2d7481e` (fix: sys.path import)

## Files Created/Modified
- `src/queries/trends.py` - KQL templates for alert_trend and alert_trend_total with summarize+bin bucketing
- `src/queries/entities.py` - KQL template for top_entities with parse_json+mv-expand entity extraction
- `src/queries/__init__.py` - Updated to merge trends and entities TEMPLATES into registry; added 180s timeouts for aggregation queries
- `src/sentinel_client.py` - Added get_alert_trend() and get_top_entities() methods with auto-bin selection and 180s timeout
- `tests/test_sentinel_client.py` - Added unit tests for trend and entity query methods
- `tests/smoke_live.py` - Live smoke test exercising all 5 query methods against real Sentinel workspace

## Decisions Made
- Aggregation queries use 180s server_timeout (vs 60s for simple queries) to accommodate heavier KQL operators like summarize+bin and parse_json+mv-expand
- Auto-bin selection: get_alert_trend() picks "1h" bins for short windows (last_1h, last_24h) and "1d" bins for longer windows (last_3d through last_30d), caller can override
- Entity extraction uses KQL `parse_json(Entities)` then `mv-expand` with `case()` to normalize account/ip/host entity types into a single ranked list

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added sys.path fix to smoke test for direct execution**
- **Found during:** Task 2 (live verification checkpoint)
- **Issue:** Running `python -m tests.smoke_live` from project root failed to resolve `src` imports when the project root was not on sys.path
- **Fix:** Added `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` at top of smoke_live.py
- **Files modified:** tests/smoke_live.py
- **Verification:** Smoke test runs successfully from project root
- **Committed in:** 2d7481e

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor import path fix. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete Sentinel data access layer with 5 query methods ready for Phase 3 tool definitions
- SentinelClient methods return typed dataclasses (Incident, Alert, TrendPoint, EntityCount) with metadata envelopes -- ready for LLM tool result formatting
- All methods validate inputs (time windows, severity, limits) and handle partial results, timeouts, and errors
- Phase 3 will wrap these methods as OpenAI function calling tools for the AI orchestration loop

## Self-Check: PASSED

- All 6 key files verified on disk (trends.py, entities.py, smoke_live.py, __init__.py, sentinel_client.py, test_sentinel_client.py)
- Commit f021321 (Task 1) verified in git log
- Commit cb5454b (Task 2 smoke test) verified in git log
- Commit 2d7481e (Task 2 sys.path fix) verified in git log
- 9 templates in TEMPLATE_REGISTRY confirmed

---
*Phase: 02-sentinel-data-access*
*Completed: 2026-02-18*
