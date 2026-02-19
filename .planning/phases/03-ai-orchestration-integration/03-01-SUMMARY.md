---
phase: 03-ai-orchestration-integration
plan: 01
subsystem: ai-orchestration
tags: [openai, function-calling, tool-dispatch, system-prompt, tiktoken]

# Dependency graph
requires:
  - phase: 02-sentinel-data-access
    provides: "SentinelClient with 5 query methods (query_incidents, get_incident_detail, query_alerts, get_alert_trend, get_top_entities)"
provides:
  - "SENTINEL_TOOLS: 5 OpenAI tool definitions in tools parameter format"
  - "ToolDispatcher: routes tool calls to SentinelClient with retry logic"
  - "SYSTEM_PROMPT: grounded system prompt with no-fabrication rules"
  - "Prompt templates: TOKEN_WARNING, MAX_ROUNDS_MESSAGE, CLEAR_SUMMARY_TEMPLATE, DISCLAIMER"
affects: [03-ai-orchestration-integration, 05-cli-experience-polish]

# Tech tracking
tech-stack:
  added: [tiktoken]
  patterns: [tool-dispatch-with-retry, structured-error-return, no-strict-mode-tools]

key-files:
  created:
    - src/tools.py
    - src/tool_handlers.py
    - src/prompts.py
    - tests/test_tools.py
    - tests/test_tool_handlers.py
    - tests/test_prompts.py
  modified:
    - requirements.txt

key-decisions:
  - "Used getattr fallback for method.__name__ in retry logging to support MagicMock in tests"
  - "Tool descriptions split across multiple short strings for ruff E501 compliance"
  - "incident_ref typed as string in JSON schema with description guidance for int/str union (OpenAI tools don't support oneOf well)"

patterns-established:
  - "Tool dispatch pattern: ToolDispatcher._dispatch_map routes tool names to handler methods"
  - "Retry pattern: _call_with_retry checks QueryError.retry_possible, retries once silently"
  - "Status message pattern: _STATUS_MESSAGES dict with get_status_message() accessor"

requirements-completed: [ORCH-02, ORCH-03]

# Metrics
duration: 5min
completed: 2026-02-19
---

# Phase 3 Plan 01: Tool Definitions, Dispatch Handler, and System Prompt Summary

**5 OpenAI tool definitions mapping 1:1 to SentinelClient methods, ToolDispatcher with silent retry logic, and grounded system prompt with no-fabrication rules and footnote transparency**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-19T20:16:02Z
- **Completed:** 2026-02-19T20:21:18Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- 5 tool definitions in SENTINEL_TOOLS with correct parameter schemas, enums matching TIME_WINDOWS/SEVERITY_ORDER, and no strict mode
- ToolDispatcher routing all 5 tools to SentinelClient methods with silent single-retry on retryable errors
- System prompt with hard no-fabrication rule, context-poisoning guard, footnote-style data sources, and numbered result references
- 49 new tests (15 tool schema, 17 dispatch, 12 prompt content) -- 126 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Tool definitions and dispatch handler** - `b8ff183` (feat)
2. **Task 2: System prompt and templates** - `d0075c0` (feat)
3. **Task 3: Tests for tools, dispatch, and prompts** - `2da8544` (test)

## Files Created/Modified
- `src/tools.py` - SENTINEL_TOOLS list with 5 OpenAI function-calling tool definitions and get_tool_names() helper
- `src/tool_handlers.py` - ToolDispatcher class routing tool names to SentinelClient methods with retry logic
- `src/prompts.py` - SYSTEM_PROMPT, TOKEN_WARNING, MAX_ROUNDS_MESSAGE, CLEAR_SUMMARY_TEMPLATE, DISCLAIMER constants
- `tests/test_tools.py` - 15 tests for tool schema structure, enums, required params, no strict mode
- `tests/test_tool_handlers.py` - 17 tests for dispatch routing, defaults, retry logic, error handling, status messages
- `tests/test_prompts.py` - 12 tests for prompt content (grounding, transparency, templates)
- `requirements.txt` - Added tiktoken>=0.12.0 for Plan 03-02 token counting

## Decisions Made
- Used `getattr(method, "__name__", repr(method))` fallback in retry debug logging because `MagicMock` methods don't have `__name__`
- Tool descriptions use multi-line string concatenation to stay within 100-char line limit per ruff E501
- `incident_ref` typed as string in JSON schema with description guidance for integer/string union, since OpenAI tools don't support `oneOf` well without strict mode

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed method.__name__ AttributeError with MagicMock**
- **Found during:** Task 3 (test execution)
- **Issue:** `logger.debug` in `_call_with_retry` accessed `method.__name__` which fails on MagicMock objects (magic attributes raise AttributeError)
- **Fix:** Changed to `getattr(method, "__name__", repr(method))` for safe fallback
- **Files modified:** src/tool_handlers.py
- **Verification:** All 49 new tests pass including retry tests with MagicMock
- **Committed in:** 2da8544 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor defensive fix for test compatibility. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All building blocks ready for Plan 03-02 (ChatSession + CLI): tool definitions, dispatcher, and system prompt
- tiktoken pre-installed for token counting in the chat session
- 126 tests passing with no regressions

## Self-Check: PASSED

All 6 created files verified on disk. All 3 task commits verified in git log.

---
*Phase: 03-ai-orchestration-integration*
*Completed: 2026-02-19*
