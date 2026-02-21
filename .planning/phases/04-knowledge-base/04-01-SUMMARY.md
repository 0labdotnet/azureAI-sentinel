---
phase: 04-knowledge-base
plan: 01
subsystem: knowledge-base
tags: [chromadb, vector-store, embeddings, mitre-attack, stix2, rag]

# Dependency graph
requires:
  - phase: 03-ai-orchestration
    provides: "ChatSession with tool loop and ToolDispatcher for function calling"
provides:
  - "VectorStore class with two ChromaDB collections (incidents, playbooks)"
  - "20 synthetic seed incidents covering 9 attack types"
  - "5 hand-written playbooks with investigation KQL, indicators, containment, escalation"
  - "MITRE ATT&CK fetcher with 24h file caching and 25 curated techniques"
  - "MockEmbeddingFunction for testing without Azure OpenAI calls"
affects: [04-knowledge-base, 05-cli-experience]

# Tech tracking
tech-stack:
  added: [chromadb>=1.5.0, stix2>=3.0.2, requests>=2.31.0]
  patterns: [EphemeralClient test injection, MockEmbeddingFunction protocol, section-based playbook chunking, cosine distance threshold 0.35]

key-files:
  created:
    - src/vector_store.py
    - src/knowledge/__init__.py
    - src/knowledge/seed_incidents.py
    - src/knowledge/playbooks.py
    - src/mitre.py
    - tests/test_vector_store.py
    - tests/test_mitre.py
  modified:
    - requirements.txt
    - src/config.py

key-decisions:
  - "ChromaDB EphemeralClient shares state across instances; tests must delete collections before creating fresh ones"
  - "stix2 MemoryStore requires allow_custom=True for MITRE x_mitre_* extension fields"
  - "MockEmbeddingFunction implements full ChromaDB EmbeddingFunction protocol (name, build_from_config, get_config, __call__)"
  - "VectorStore accepts optional embedding_fn parameter alongside client for test injection flexibility"

patterns-established:
  - "MockEmbeddingFunction: deterministic SHA-256 hash-based embeddings for reproducible vector store tests"
  - "Section-based playbook chunking: each section becomes a separate chunk with playbook context in document text"
  - "Graceful degradation: MITRE fetcher returns empty list on any error, logs warning"

requirements-completed: [KB-01, KB-02, KB-03]

# Metrics
duration: 13min
completed: 2026-02-21
---

# Phase 4 Plan 01: Knowledge Base Data Layer Summary

**ChromaDB VectorStore with two collections, 20 synthetic incidents, 5 detailed playbooks with KQL, MITRE ATT&CK fetcher with 25 curated techniques and 24h caching**

## Performance

- **Duration:** 13 min
- **Started:** 2026-02-21T03:22:02Z
- **Completed:** 2026-02-21T03:35:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- VectorStore class with incidents and playbooks collections using cosine distance and Azure OpenAI embeddings
- 20 synthetic seed incidents covering phishing, brute force, malware, suspicious sign-in, data exfiltration, privilege escalation, lateral movement, DoS, and credential theft
- 5 hand-written playbooks with actionable investigation steps including copy-pasteable KQL queries
- MITRE ATT&CK fetcher downloading from GitHub, filtering to 25 curated techniques with 24h file caching
- Settings dataclass extended with azure_openai_embedding_deployment and chromadb_path fields
- Comprehensive tests: 21 new tests (14 vector store, 7 MITRE) all passing alongside 146 existing tests

## Task Commits

Each task was committed atomically:

1. **Task 1: VectorStore class, config updates, and dependencies** - `c9391ce` (feat)
2. **Task 2: Seed data, playbooks, MITRE fetcher, and tests** - `6427d33` (feat)

## Files Created/Modified
- `src/vector_store.py` - VectorStore class with upsert, search, confidence flagging, and collection counts
- `src/knowledge/__init__.py` - Empty package init for knowledge module
- `src/knowledge/seed_incidents.py` - 20 synthetic incidents with build_incident_document and build_incident_metadata helpers
- `src/knowledge/playbooks.py` - 5 detailed playbooks with build_playbook_chunks helper
- `src/mitre.py` - MITRE ATT&CK fetcher with 25 curated technique IDs and file caching
- `tests/test_vector_store.py` - 14 tests covering upsert, search, confidence flagging, counts
- `tests/test_mitre.py` - 7 tests covering parsing, caching, graceful failure, curated list
- `requirements.txt` - Added chromadb>=1.5.0, stix2>=3.0.2, requests>=2.31.0
- `src/config.py` - Added embedding_deployment and chromadb_path to Settings and load_settings()

## Decisions Made
- ChromaDB EphemeralClient shares in-process state across instances, so test fixture must delete collections before each test for isolation
- stix2 v3.0.2 requires `allow_custom=True` on MemoryStore to handle MITRE's `x_mitre_is_subtechnique` custom STIX extension field
- MockEmbeddingFunction must implement full ChromaDB v1.5.x EmbeddingFunction protocol (not just `__call__`) including `name()`, `build_from_config()`, `get_config()`, and `__init__()`
- VectorStore constructor accepts optional `embedding_fn` parameter (in addition to `client`) to enable test injection of mock embedding functions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] stix2 MemoryStore requires allow_custom=True**
- **Found during:** Task 2 (MITRE fetcher and tests)
- **Issue:** MITRE ATT&CK STIX objects use custom extension properties (x_mitre_is_subtechnique) that stix2 v3.0.2 rejects by default
- **Fix:** Added `allow_custom=True` to `MemoryStore()` constructor call
- **Files modified:** src/mitre.py
- **Verification:** All MITRE tests pass with valid STIX parsing
- **Committed in:** 6427d33 (Task 2 commit)

**2. [Rule 3 - Blocking] ChromaDB v1.5.x EmbeddingFunction protocol changes**
- **Found during:** Task 2 (VectorStore tests)
- **Issue:** ChromaDB v1.5.x requires EmbeddingFunction implementations to provide `name()`, `embed_query()`, `build_from_config()`, and `get_config()` methods. The initial MockEmbeddingFunction only had `__call__`.
- **Fix:** Made MockEmbeddingFunction inherit from `chromadb.EmbeddingFunction[Documents]` and implement all required protocol methods
- **Files modified:** tests/test_vector_store.py
- **Verification:** All vector store tests pass with proper embedding function protocol
- **Committed in:** 6427d33 (Task 2 commit)

**3. [Rule 3 - Blocking] ChromaDB EphemeralClient shared state across test fixtures**
- **Found during:** Task 2 (VectorStore tests)
- **Issue:** `chromadb.EphemeralClient()` shares in-process state between instances, so collections from one test leaked into subsequent tests
- **Fix:** Added collection deletion cleanup in the vector_store fixture before creating fresh collections
- **Files modified:** tests/test_vector_store.py
- **Verification:** TestGetCollectionCounts.test_initial_counts_are_zero now correctly sees 0/0
- **Committed in:** 6427d33 (Task 2 commit)

**4. [Rule 1 - Bug] Added embedding_fn parameter to VectorStore constructor**
- **Found during:** Task 1 (VectorStore class design)
- **Issue:** Plan specified optional `client` parameter for DI but tests also need to inject a mock embedding function to avoid Azure OpenAI calls
- **Fix:** Added optional `embedding_fn` parameter to VectorStore constructor
- **Files modified:** src/vector_store.py
- **Verification:** Tests can inject MockEmbeddingFunction successfully
- **Committed in:** c9391ce (Task 1 commit)

---

**Total deviations:** 4 auto-fixed (1 bug, 3 blocking)
**Impact on plan:** All auto-fixes necessary for correctness with chromadb v1.5.x and stix2 v3.0.2 APIs. No scope creep.

## Issues Encountered
- STIX mock data in tests required valid v4 UUIDs (not placeholder IDs) for stix2 v3.0.2 strict validation
- ChromaDB DeprecationWarning about legacy embedding function config (cosmetic, does not affect functionality)

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- VectorStore, seed data, playbooks, and MITRE fetcher are ready for Plan 02 integration
- Plan 02 will wire KB tools into the existing tool loop, add startup ingestion, and update system prompt
- All new code has test coverage and follows existing project DI patterns

## Self-Check: PASSED

- All 7 created files exist on disk
- Both commit hashes (c9391ce, 6427d33) found in git log
- 167 tests pass (146 existing + 21 new)
- ruff lint clean on all new/modified files

---
*Phase: 04-knowledge-base*
*Completed: 2026-02-21*
