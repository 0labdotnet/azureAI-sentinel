---
phase: 04-knowledge-base
plan: 02
subsystem: knowledge-base
tags: [chromadb, vector-store, tool-calling, rag, mitre-attack, openai-tools]

# Dependency graph
requires:
  - phase: 04-knowledge-base
    plan: 01
    provides: "VectorStore class, seed incidents, playbooks, MITRE fetcher"
  - phase: 03-ai-orchestration
    provides: "ChatSession with tool loop, ToolDispatcher, SENTINEL_TOOLS"
provides:
  - "3 KB tool definitions (search_similar_incidents, search_playbooks, get_investigation_guidance)"
  - "ToolDispatcher routing KB tool calls to VectorStore methods with graceful None fallback"
  - "System prompt KB guidance section with result presentation rules"
  - "ChatSession passing combined Sentinel+KB tools to LLM"
  - "Startup ingestion pipeline: seed data, playbooks, live Sentinel incidents, MITRE ATT&CK"
  - "Graceful degradation: chatbot runs Sentinel-only if KB unavailable"
affects: [05-cli-experience]

# Tech tracking
tech-stack:
  added: []
  patterns: [optional vector_store DI in ToolDispatcher and ChatSession, startup ingestion pipeline with graceful failure, combined tool list pattern]

key-files:
  created: []
  modified:
    - src/tools.py
    - src/tool_handlers.py
    - src/prompts.py
    - src/openai_client.py
    - src/main.py
    - tests/test_tools.py
    - tests/test_tool_handlers.py
    - tests/test_main.py
    - tests/test_openai_client.py

key-decisions:
  - "KB tools registered in dispatch_map only when vector_store is not None (not registered as error-returning stubs)"
  - "get_investigation_guidance combines both playbook and incident search results for comprehensive MITRE-mapped guidance"
  - "Startup pipeline extracted to _init_knowledge_base() helper for testability and clean separation"
  - "Live Sentinel incidents ingested with graceful failure -- chatbot starts even if Sentinel is unreachable"

patterns-established:
  - "Optional vector_store parameter: ToolDispatcher and ChatSession accept VectorStore|None, extending project DI pattern"
  - "Combined tool list: self._tools = SENTINEL_TOOLS + KB_TOOLS when VS available, else SENTINEL_TOOLS only"
  - "Startup ingestion: _init_knowledge_base() returns VectorStore or None, caller handles graceful degradation"

requirements-completed: [KB-01, KB-02, KB-03]

# Metrics
duration: 6min
completed: 2026-02-21
---

# Phase 4 Plan 02: KB Integration and Startup Pipeline Summary

**3 KB tools wired into chatbot tool loop with startup ingestion of seed data, live incidents, playbooks, and MITRE techniques -- full hybrid RAG architecture operational**

## Performance

- **Duration:** 6 min
- **Started:** 2026-02-21T03:38:25Z
- **Completed:** 2026-02-21T03:44:22Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- 3 KB tool definitions (search_similar_incidents, search_playbooks, get_investigation_guidance) added to tools.py and wired through ToolDispatcher to VectorStore
- System prompt updated with KB tool usage guidance and result presentation rules (separate "Similar past incidents" and "Relevant playbooks" sections, low-confidence warnings)
- ChatSession passes combined 8-tool list (5 Sentinel + 3 KB) to LLM when VectorStore is available
- Startup ingestion pipeline loads seed incidents, playbook chunks, live Sentinel incidents (last 30 days), and MITRE ATT&CK techniques
- Full graceful degradation: if VectorStore creation fails, chatbot runs with Sentinel-only tools
- 187 tests pass including 20 new tests (KB tools, dispatch routing, startup, ChatSession tool counts)

## Task Commits

Each task was committed atomically:

1. **Task 1: KB tool definitions, dispatcher wiring, and system prompt update** - `77b7a20` (feat)
2. **Task 2: Startup ingestion pipeline, updated tests, and end-to-end wiring** - `7ea6e60` (feat)

## Files Created/Modified
- `src/tools.py` - Added KB_TOOLS list with 3 tool definitions, updated get_tool_names() to return 8 tools
- `src/tool_handlers.py` - ToolDispatcher accepts optional VectorStore, routes KB tools to VectorStore methods
- `src/prompts.py` - System prompt with KB tool guidance section and result presentation rules
- `src/openai_client.py` - ChatSession accepts optional VectorStore, passes combined tool list to LLM
- `src/main.py` - Startup pipeline via _init_knowledge_base(), welcome banner updated, VectorStore passed to ChatSession
- `tests/test_tools.py` - Added TestKBToolDefinitions class, updated TestGetToolNames for 8 tools
- `tests/test_tool_handlers.py` - Added TestKBDispatchNoVectorStore and TestKBDispatchWithVectorStore classes
- `tests/test_main.py` - All tests mock _init_knowledge_base, added TestKnowledgeBaseStartup class
- `tests/test_openai_client.py` - Added TestChatSessionWithVectorStore verifying 8 vs 5 tool counts

## Decisions Made
- KB tools are only added to ToolDispatcher's dispatch_map when vector_store is not None. When vector_store is None, KB tool names hit the "Unknown tool" fallback rather than a dedicated error handler. This keeps the dispatch_map clean and makes the "KB unavailable" state obvious.
- get_investigation_guidance combines both playbook search and incident search to provide comprehensive MITRE-mapped guidance rather than querying only one collection.
- Startup ingestion extracted to _init_knowledge_base() helper function for testability -- tests can mock a single function instead of patching multiple imports.
- Live Sentinel incident ingestion uses last_30d window with Informational severity and 100 limit to capture a broad baseline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing line-too-long in main.py conversation clear banner**
- **Found during:** Task 2 (main.py rewrite)
- **Issue:** The original "Conversation cleared" separator line exceeded ruff's 100-char line limit (110 chars)
- **Fix:** Shortened the separator line to fit within 100 characters
- **Files modified:** src/main.py
- **Verification:** ruff check passes on src/main.py
- **Committed in:** 7ea6e60 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Cosmetic fix only. No scope creep.

## Issues Encountered
None -- both tasks executed cleanly with all tests passing.

## User Setup Required
None - no external service configuration required. Knowledge base uses existing Azure OpenAI embedding deployment and ChromaDB storage path from Settings.

## Next Phase Readiness
- Full hybrid RAG architecture is now operational: user asks natural language -> LLM selects appropriate tool (Sentinel or KB) -> results synthesized
- Phase 4 is complete -- all KB requirements (KB-01, KB-02, KB-03) fully satisfied
- Ready for Phase 5 (CLI Experience) which can build on the complete tool set

## Self-Check: PASSED

- All 9 modified files exist on disk
- Both commit hashes (77b7a20, 7ea6e60) found in git log
- 187 tests pass (167 existing + 20 new)
- ruff lint clean on all modified files

---
*Phase: 04-knowledge-base*
*Completed: 2026-02-21*
