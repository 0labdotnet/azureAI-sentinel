---
status: diagnosed
phase: 03-ai-orchestration-integration
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-19T21:30:00Z
updated: 2026-02-19T21:48:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Start the Chatbot
expected: Running `python -m src` launches the chatbot with a welcome banner and an input prompt ready for your query.
result: pass

### 2. Natural Language Incident Query
expected: Asking a natural language question like "show me high severity incidents from the last 24 hours" returns a synthesized answer listing real incidents from Sentinel with details like incident numbers, titles, and severities.
result: pass

### 3. Tool Usage Transparency
expected: The chatbot's response indicates which tools or data sources it used (e.g., mentions querying incidents, searching alerts) so you can see reasoning transparency.
result: pass

### 4. Grounded Responses (No Fabrication)
expected: All incident numbers, severities, timestamps, and titles in the response match real Sentinel data. Nothing appears made up or hallucinated.
result: pass
note: "Data is accurate (no fabrication). Two UX issues recorded separately: missing incident numbers in list view (gap 1, major) and UTC timestamps without timezone adjustment (gap 2, minor)."

### 5. Multi-turn Conversation
expected: After the initial query, asking a follow-up like "tell me more about incident #X" (referencing one from the previous answer) returns detailed information about that specific incident, demonstrating context retention.
result: pass

### 6. /clear Command
expected: Typing `/clear` clears the terminal screen and shows a summary of the previous conversation. The chatbot continues to work for new queries after clearing.
result: pass

### 7. /quit Command
expected: Typing `/quit` or `/exit` cleanly exits the chatbot with a goodbye message. No errors or stack traces.
result: pass

## Summary

total: 7
passed: 7
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Incident numbers are included when listing incidents so users can reference them"
  status: failed
  reason: "User reported: incident number is not included with the returned results- we should make sure that is included with listed incidents and not just in incident details that have to be asked for."
  severity: major
  test: 4
  root_cause: "System prompt [1]/[2]/[3] formatting rule causes LLM to use positional indices instead of displaying the Sentinel incident number field. Data is present at every pipeline stage (KQL, parser, model, projection) but the prompt gives no instruction to surface the number field."
  artifacts:
    - path: "src/prompts.py"
      issue: "Response formatting rule uses positional [1]/[2]/[3] indices with no instruction to also display Sentinel incident numbers"
  missing:
    - "Add system prompt instruction to display Sentinel incident number (#N) in each list entry"
  debug_session: ".planning/debug/incident-number-missing-list.md"

- truth: "Timestamps are presented in the user's local timezone or clearly labeled as UTC"
  status: failed
  reason: "User reported: The chatbot is presenting timestamps as UTC currently- so it is not hallucinating, but it may confuse users that timestamps are not being adjusted for their timezone/locale."
  severity: minor
  test: 4
  root_cause: "Three compounding gaps: (1) format_relative_time() in models.py produces 'yesterday at 3:14 PM' from UTC datetime with no timezone label, (2) system prompt has zero timezone handling instructions, (3) to_dict() serializes as +00:00 instead of Z suffix."
  artifacts:
    - path: "src/models.py"
      issue: "format_relative_time() yesterday branch omits UTC label; to_dict() uses +00:00 instead of Z"
    - path: "src/prompts.py"
      issue: "No timezone labeling instruction in SYSTEM_PROMPT"
  missing:
    - "Append ' UTC' to format_relative_time() yesterday branch"
    - "Add UTC labeling rule to SYSTEM_PROMPT"
  debug_session: ".planning/debug/timestamp-utc-labeling.md"
