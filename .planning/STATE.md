# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** SOC analysts can get answers about their security environment in seconds using plain English -- no KQL knowledge required -- with live data grounded in real Sentinel incidents and enriched by historical context.
**Current focus:** Phase 3: AI Orchestration & Integration

## Current Position

Phase: 3 of 6 (AI Orchestration & Integration)
Plan: 2 of 2 in current phase
Status: Plan 03-01 complete, Plan 03-02 next
Last activity: 2026-02-19 -- Plan 03-01 complete (tool definitions, dispatch handler, system prompt)

Progress: [█████░░░░░] 42%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 11min (automated only)
- Total execution time: 0.67 hours (automated only)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2 | 8min + manual | 8min (auto) |
| 2. Sentinel Data Access | 2 | 27min | 14min |
| 3. AI Orchestration | 1 (of 2) | 5min | 5min |

**Recent Trend:**
- Last 5 plans: 01-02 (8min), 02-01 (9min), 02-02 (18min), 03-01 (5min)
- Trend: Plan 03-01 complete, continuing Phase 3

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Content filter modification request submitted (pending 1-3 business day approval). High-only filter is working fallback.
- [Roadmap]: Phases 2 and 3 are sequential (not parallel) because orchestration integration depends on a working Sentinel client
- [01-01]: Azure OpenAI resource named oai-sentinel-dev in East US 2
- [01-01]: Content filter "security-permissive" set to High-only on all 4 harm categories
- [01-01]: Renamed sentinel-dev.env to .env for python-dotenv compatibility
- [01-01]: Venv recreated with Python 3.14.2 (3.12 no longer on system)
- [01-01]: Fixed clean_env fixture to patch load_dotenv when .env exists on disk
- [01-02]: Added __test__ = False markers to connectivity check functions to prevent pytest collection conflicts
- [02-01]: entity_count defaults to 0 in incident list view; populated from entity sub-query in get_incident_detail()
- [02-01]: SentinelClient accepts optional client param for test injection (no credential mocking needed)
- [02-01]: Used datetime.UTC alias throughout per ruff UP017 (Python 3.11+)
- [02-01]: get_incident_detail() uses 30-day time window for lookups to find older incidents
- [02-02]: Aggregation queries (trend, entity) use 180s server_timeout vs 60s for simple queries
- [02-02]: Auto-select bin_size: 1h for short windows (last_1h/last_24h), 1d for longer (last_3d+)
- [02-02]: Entity extraction uses parse_json + mv-expand KQL pattern with case() for account/ip/host types
- [03-01]: incident_ref typed as string in JSON schema with description guidance for int/str union (OpenAI tools don't support oneOf well)
- [03-01]: Used getattr fallback for method.__name__ in retry logging to support MagicMock in tests
- [03-01]: No strict mode on tool schemas (incompatible with parallel tool calls)

### Pending Todos

None yet.

### Blockers/Concerns

- Content filter modification approval timeline is outside team control (1-3 business days). High-only filter works as fallback — "Hello, respond with OK" test passes. May need to test with actual security content once approval comes through.
- Python runtime: .venv now uses Python 3.14.2 (pyproject.toml specifies >=3.11,<3.14 — may need to relax upper bound)

## Session Continuity

Last session: 2026-02-19
Stopped at: Completed 03-01-PLAN.md
Resume file: .planning/phases/03-ai-orchestration-integration/03-01-SUMMARY.md
