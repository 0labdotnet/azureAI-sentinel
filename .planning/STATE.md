# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** SOC analysts can get answers about their security environment in seconds using plain English -- no KQL knowledge required -- with live data grounded in real Sentinel incidents and enriched by historical context.
**Current focus:** Phase 5: CLI Experience

## Current Position

Phase: 5 of 6 (CLI Experience)
Plan: 1 of ? in current phase
Status: Phase 4 complete, Phase 5 next
Last activity: 2026-02-21 -- Plan 04-02 complete (KB integration, startup pipeline, full hybrid RAG)

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 10min (automated only)
- Total execution time: 1.22 hours (automated only)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation | 2 | 8min + manual | 8min (auto) |
| 2. Sentinel Data Access | 2 | 27min | 14min |
| 3. AI Orchestration | 3 (of 3) | 37min | 12min |
| 4. Knowledge Base | 2 (of 2) | 19min | 10min |

**Recent Trend:**
- Last 5 plans: 03-01 (5min), 03-02 (~30min), 03-03 (2min), 04-01 (13min), 04-02 (6min)
- Trend: Phase 4 complete

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
- [03-02]: ChatSession combines OpenAI client, tool loop, and conversation management in one class (no separate orchestrator for POC)
- [03-02]: Optional client/sentinel_client constructor params for test injection (same pattern as SentinelClient)
- [03-02]: System prompt prepended on each API call, not stored in message history
- [03-02]: ANSI escape codes used for /clear terminal screen clearing
- [03-03]: Only yesterday branch gets UTC label -- other branches are relative and self-explanatory
- [03-03]: Incident number shown as '#N [pos]' format combining Sentinel number with positional index
- [04-01]: VectorStore accepts optional client and embedding_fn params for test DI (extends project pattern)
- [04-01]: stix2 MemoryStore needs allow_custom=True for MITRE x_mitre_* extension fields
- [04-01]: ChromaDB EphemeralClient shares in-process state; tests must delete collections before each test
- [04-01]: MockEmbeddingFunction must implement full EmbeddingFunction protocol for ChromaDB v1.5.x
- [04-02]: KB tools registered in dispatch_map only when vector_store is not None (Unknown tool fallback otherwise)
- [04-02]: get_investigation_guidance combines playbook + incident search for comprehensive MITRE-mapped guidance
- [04-02]: Startup ingestion extracted to _init_knowledge_base() helper for testability
- [04-02]: Live Sentinel incidents ingested with graceful failure; chatbot starts even if Sentinel unreachable

### Pending Todos

None yet.

### Blockers/Concerns

- Content filter modification approval timeline is outside team control (1-3 business days). High-only filter works as fallback — "Hello, respond with OK" test passes. May need to test with actual security content once approval comes through.
- Python runtime: .venv now uses Python 3.14.2 (pyproject.toml specifies >=3.11,<3.14 — may need to relax upper bound)

## Session Continuity

Last session: 2026-02-21
Stopped at: Completed 04-02-PLAN.md (Phase 4 complete)
Resume file: .planning/phases/05-cli-experience/ (Phase 5 planning needed)
