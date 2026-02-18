# Phase 2: Sentinel Data Access - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

KQL template registry and Sentinel client that can execute all pre-defined query templates and return structured, field-projected results from live Sentinel data. Covers incidents, alerts, trends, and entities. Retry logic, throttling, and partial result handling included. AI orchestration and tool dispatch are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Query parameterization
- Time ranges use predefined windows only: 'last_1h', 'last_24h', 'last_7d', 'last_30d' — no freeform datetime parsing
- Severity filtering uses a minimum threshold model (e.g., 'Medium' returns Medium + High + Critical)
- Severity is optional with a default of 'Informational' (returns all severities when omitted)
- Incident detail lookups accept either incident number (integer) or incident name/title (string match)

### Response shape & projections
- Query results returned as typed dataclasses (e.g., Incident, Alert, TrendPoint)
- Incident lists include summary + counts: number, title, severity, status, created time, alert count, entity count, last update time
- Timestamps formatted as human-readable relative strings (e.g., '2 hours ago', 'yesterday at 3:14 PM')
- Every query result wrapped in a metadata envelope: {metadata: {total, query_ms, truncated}, results: [...]}

### KQL template organization
- Templates organized in per-domain modules (incidents.py, alerts.py, trends.py, entities.py)
- Parameter substitution uses named placeholders with a builder function that validates params, applies defaults, and substitutes safely
- Field projections managed via a separate projection config (not baked into KQL templates) — allows templates to return full rows, with projection applied post-query
- Result limits are caller-controlled with a hard cap and a sensible default when caller doesn't specify

### Resilience behavior
- Standard retry: 3 retries with exponential backoff (1s, 2s, 4s) on transient failures (network errors, 5xx, 429)
- Partial results: return whatever came back with a 'truncated' flag in metadata — LLM tells user results may be incomplete
- Timeouts: per-template configuration (trend/aggregation queries get longer timeouts than simple lookups)
- Errors surfaced as structured error objects with code, message, and retry_possible flag — when retry is not possible, the LLM must pass error code + message directly to the user

### Claude's Discretion
- Exact predefined time window set (whether to include last_3d, last_14d, etc.)
- Default and max result limits per query type
- Specific dataclass field names and serialization format
- Exact backoff timing and jitter strategy
- How incident name matching works (substring, fuzzy, exact)
- Projection config format and location

</decisions>

<specifics>
## Specific Ideas

- Severity threshold model should map to Sentinel's actual severity enum: Informational < Low < Medium < High (Critical may not exist in SecurityIncident — verify during research)
- The metadata envelope pattern enables the LLM to say "Found 47 incidents, showing top 20" even when results are capped
- Per-template timeouts acknowledge that `summarize` / `make-series` KQL operators are significantly heavier than simple `where` + `take` queries

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-sentinel-data-access*
*Context gathered: 2026-02-18*
