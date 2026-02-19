# Phase 3: AI Orchestration & Integration - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can have multi-turn natural language conversations that invoke Sentinel tools and receive grounded, accurate responses with reasoning transparency. This phase delivers the OpenAI tool loop, tool dispatch, conversation management, and end-to-end natural language querying. Knowledge base (ChromaDB/RAG), rich CLI formatting, and demo preparation belong in later phases.

</domain>

<decisions>
## Implementation Decisions

### Conversation flow
- Support both implicit references ("tell me more about that incident") and numbered references ([1], [2], [3]) in result lists — users will naturally use both
- Default conversation memory window: 30 turns, configurable in settings (will tune experimentally for token/context balance)
- When approaching token limit: warn the user ("Context getting long, older messages will be trimmed"), then truncate oldest messages
- On /clear: preserve user preferences and generate a summary of key discussion items that carries forward as condensed context — user doesn't completely lose session context

### Response style
- Default verbosity: explanatory — present data with brief context and interpretation (not terse, not verbose walkthrough)
- Reasoning transparency: footnote style — answer first, then a section below listing which tools were called and what data was retrieved
- Data formatting: basic readable tables in Phase 3 — rich formatting, color-coding, and severity indicators added in Phase 5
- Follow-up suggestions: only when helpful for complex results (e.g., incident lists), not after every response

### Tool invocation UX
- Simple text status messages during tool execution in Phase 3 (e.g., "Querying incidents...") — spinners and progress bars in Phase 5
- Error handling: retry silently once on failure, then explain the error clearly with actionable suggestions if retry also fails
- Parallel tool calls: yes, when the question warrants it (e.g., broad queries that benefit from concurrent incident + alert queries)
- MAX_TOOL_ROUNDS = 5: only surface the limit when reached ("Reached maximum tool rounds. Here's what I found so far.")
- Max tool rounds configurable in settings but not exposed in user-facing UI

### Grounding & safety
- Data presentation: facts first from tool results, then offer deeper analysis as opt-in ("Would you like me to analyze potential implications?") with human-verification disclaimer
- Empty results: state clearly, then suggest alternatives (broaden severity, expand time range)
- Out-of-scope questions: explain what the chatbot CAN do, keep it friendly with business-appropriate humor — light jokes and puns encouraged; nothing crude, violent, sexual, racist, or otherwise distasteful
- **Hard rule: never fabricate data.** No synthetic incident numbers, severities, timestamps, or example data under any circumstances. If asked for examples, respond: "I'm not allowed to provide example data to prevent context poisoning. Let me query some real data..."
- All AI-generated analysis must carry a disclaimer that it should be verified by a human before taking action

### Claude's Discretion
- Exact system prompt wording and personality tuning
- Token budget allocation strategy across conversation turns
- Specific retry logic implementation (exponential backoff, etc.)
- How the /clear summary is structured internally
- Loading skeleton / waiting state phrasing

</decisions>

<specifics>
## Specific Ideas

- Numbered result references (e.g., [1], [2]) for explicit drill-down alongside natural implicit references ("that incident")
- /clear summary concept: don't fully wipe context — carry forward a condensed summary of key discussion items and preferences
- "Context poisoning" framing when explaining why fabrication is blocked — communicates the rationale to the user in security terms they understand
- Friendly personality with appropriate humor for out-of-scope redirects — makes the tool approachable for SOC teams

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-ai-orchestration-integration*
*Context gathered: 2026-02-19*
