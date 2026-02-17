# Project Research Summary

**Project:** Sentinel RAG Chatbot POC
**Domain:** Agentic RAG security chatbot (Python CLI / Azure OpenAI / Microsoft Sentinel)
**Researched:** 2026-02-16
**Confidence:** HIGH

## Executive Summary

This is an agentic RAG application in the security operations domain: a Python CLI chatbot that gives SOC analysts natural language access to Microsoft Sentinel SIEM data. The recommended architecture is a hybrid approach — OpenAI function calling for live Sentinel data retrieval combined with ChromaDB semantic search for historical incident context and playbooks. Experts building this type of system use pre-defined, parameterized KQL query templates (never freeform KQL generation), a tight tool loop with a hard cap on iterations, and careful token budget management, because Sentinel data is verbose enough to blow the 128K context window in just a few tool calls.

The recommended stack is mature and low-risk: `openai` v2.x with the `tools` parameter (not the deprecated `functions` API), `azure-monitor-query` v2.0.0 for KQL execution (the `azure-mgmt-securityinsight` package is effectively abandoned since 2022), `chromadb` v1.5.0 for the local vector store, and `rich` for polished terminal output. All design decisions in the existing CLAUDE.md have been validated by research — no corrections needed to the existing architecture. The no-LangChain decision is correct: the tool loop is about 50 lines of code without it, and it is far easier to debug for a leadership demo.

The two highest-priority risks are content filtering and token bloat. Azure OpenAI's default content filters block legitimate security content (malware names, MITRE technique descriptions, phishing artifacts) and must be addressed in a content filter modification request before development starts. Token budget overflow is structural: without `| project` column selection in every KQL query and a token counting layer in `openai_client.py`, a single multi-incident query will exceed the context window. Both pitfalls have clear mitigations but must be designed in from day one, not retrofitted.

---

## Key Findings

### Recommended Stack

All package versions were verified against PyPI on 2026-02-16. The stack is a clean, minimal set with no unnecessary dependencies. LangChain, `azure-search-documents`, and the Microsoft Graph SDK are explicitly excluded from the POC scope. Every technology choice has a direct functional requirement.

**Core technologies:**

- `openai >= 2.21.0`: Azure OpenAI chat completions and embeddings — v2.x is the active branch; v1.x is maintenance-only. Use `tools` parameter, not deprecated `functions`.
- `azure-monitor-query >= 2.0.0`: KQL execution via `LogsQueryClient` — the only maintained SDK for querying Sentinel data. `azure-mgmt-securityinsight` was last updated July 2022 and must not be used.
- `azure-identity >= 1.25.0`: `DefaultAzureCredential` for unified Azure auth — supports `az login` for dev and service principal for CI/production.
- `chromadb >= 1.5.0`: Local persistent vector store — zero-config setup, built-in metadata filtering, no Azure resource provisioning required. Correct choice for POC; migrate to Azure AI Search for production.
- `rich >= 14.0.0`: Terminal formatting — tables for incident lists, color-coded severity, markdown rendering for LLM responses, spinners during API calls.
- `tiktoken >= 0.12.0`: Token counting — required for enforcing the token budget system; not optional.
- `requests >= 2.32.0`: HTTP client for Sentinel REST API endpoints not covered by `azure-monitor-query` (incident management, entity enrichment).
- `python-dotenv >= 1.0.0`: Environment configuration loading.

**Python version note:** The system has Python 3.14.3 installed. Use Python 3.11 or 3.12 in the project venv — ChromaDB 1.5.0 may not have prebuilt wheels for 3.14, which would require compiling native extensions.

See `.planning/research/STACK.md` for full version table, alternatives considered, and recommended `requirements.txt` / `pyproject.toml` content.

### Expected Features

SOC analyst tools live or die on accuracy and speed. The two audiences (leadership demo and analyst trial) have different definitions of success. Leadership needs "wow" moments; analysts need to answer real questions faster than the current KQL-manual workflow.

**Must have (table stakes) — Week 1:**
- Natural language incident querying (T1) — this IS the product
- Incident detail drill-down (T2) — analysts always ask "tell me more about X"
- Alert querying and filtering (T6) — incidents need underlying alert evidence
- Multi-turn conversation with context (T3) — SOC investigation is inherently multi-step
- Grounded, accurate responses (T4) — one hallucinated severity level destroys analyst trust permanently
- Formatted output with color-coded severity (T5) — `rich` tables and colors; low effort, high polish
- Error handling with clear messages (T7) — stack traces in a demo are disqualifying

**Should have (differentiators) — Week 2, first half:**
- Investigation guidance with MITRE ATT&CK mapping (D1) — highest demo impact; what Security Copilot does
- Historical pattern matching via ChromaDB (D2) — the RAG value proposition; justifies the vector store
- Alert trend analysis (D4) — low implementation effort, strong demo value
- Entity investigation: top-targeted users/IPs (D5) — practical analyst feature
- Visible parallel tool execution (D7) — "Querying incidents... Searching knowledge base..." makes the AI feel intelligent

**Demo polish — Week 2, second half:**
- Security posture summary (D3) — ideal demo closer; parallel tool calls synthesized into executive briefing
- Explanation of reasoning (D8) — transparency builds trust
- Connection status check (`/status`) and session commands (`/clear`, `/quit`)
- Playbook-guided response (D6) — requires seeding ChromaDB with content
- Cost comparison framing in demo script (D9)

**Defer to post-POC (anti-features to avoid building now):**
- Freeform KQL generation — LLMs produce syntactically valid but semantically wrong KQL; pre-defined templates are safer
- Write operations (close/assign incidents) — violates read-only safety constraint; catastrophic if triggered in a demo
- Web UI or API server — doubles scope; CLI with `rich` is sufficient
- Streaming responses — marginal UX gain; spinner is sufficient for a POC
- Multi-workspace or multi-tenant support

See `.planning/research/FEATURES.md` for the full feature matrix, competitor comparison against Security Copilot, and feature dependency graph.

### Architecture Approach

The architecture follows a four-layer pattern: Presentation (`main.py` CLI), Orchestration (`openai_client.py` tool loop + `tool_handlers.py` dispatcher), Data Access (`sentinel_client.py` live + `vector_store.py` historical), and Foundation (`config.py` + `azure-identity`). Each layer has a single responsibility, and all Azure clients are created once at startup and injected into downstream components — never instantiated inside handler functions.

**Major components:**

1. `openai_client.py` — Conversation manager: maintains message history, runs the tool loop (LLM call -> detect tool_calls -> execute -> re-send -> repeat up to MAX_TOOL_ROUNDS=5), manages token budget via tiktoken.
2. `sentinel_client.py` — Live data layer: executes pre-defined KQL templates via `LogsQueryClient`, calls Sentinel REST API for incident management data, handles retry logic and partial results.
3. `vector_store.py` — Knowledge layer: ChromaDB semantic search for historical incidents and playbooks, embedding generation via Azure OpenAI `text-embedding-3-large` at 1024 dimensions.
4. `tool_handlers.py` — Dispatch table: maps tool names to handler functions; each handler wraps execution in try/except and returns a JSON error string on failure (never raises, always returns a string).
5. `tools.py` + `prompts.py` — Pure data: tool JSON schemas and system prompt constants; no runtime logic, no imports.
6. `main.py` — CLI boundary: user input capture, `rich` rendering, slash command dispatch; no business logic.
7. `config.py` — Single source of truth for all settings, loaded from `.env`.

**Key patterns to follow (from architecture research):**
- Tool loop with MAX_TOOL_ROUNDS guard (5 maximum per query)
- Dispatch table pattern for tool handlers (not if/elif chains)
- KQL Template Registry — parameterized templates, not freeform generation
- Token budgeting via tiktoken — enforce budgets for system prompt, tool definitions, tool results, response, and history
- Error wrapping in every tool handler — LLM explains failures in natural language

See `.planning/research/ARCHITECTURE.md` for complete diagrams, code examples for each pattern, and the build order dependency chain.

### Critical Pitfalls

1. **Content filters blocking security data** — Azure OpenAI's default filters flag malware names, MITRE technique descriptions, and phishing content as policy violations. Submit a content filter modification request in Azure AI Foundry before development begins. Test with real security data in Phase 2, not sanitized samples. Detect `finish_reason: "content_filter"` in API responses and surface a user-friendly message.

2. **Token budget overflow from verbose Sentinel data** — 10-20 incidents serialized to JSON can consume 30,000-50,000 tokens, exhausting the 128K context window. Mitigation is structural: always use `| project` in KQL to select only needed columns, implement tiktoken-based token counting from day one, set conservative `max_results` defaults (10-20 items), and return summary-first responses ("Found 47 incidents, showing top 10").

3. **Strict mode and parallel function calls are mutually exclusive** — `"strict": True` in tool definitions is incompatible with parallel function calling (per official docs). Recommendation: drop `strict: True` and keep parallel function calls enabled. Parallel tool execution provides meaningful latency reduction for multi-tool queries (the "security posture summary" feature calls 3+ tools simultaneously).

4. **Log Analytics query throttling** — The API enforces 5 concurrent queries per user and 200 requests per 30 seconds. A single conversational turn can trigger 3-5 KQL tool calls, easily hitting the concurrency limit. Use `LogsBatchQuery` to combine multiple queries into one API call; implement retry logic with exponential backoff for HTTP 429 responses; cache query results for the duration of a session.

5. **Tool description length limit (1,024 characters)** — Azure OpenAI silently truncates tool descriptions above 1,024 characters. With 6+ tools having detailed descriptions, this is easy to hit. Keep descriptions under 800 characters; move detailed guidance into the system prompt where the token budget is larger.

6. **ChromaDB embedding model mismatch** — Using different embedding models or dimension settings for ingestion vs. query produces silently wrong retrieval results. Enforce consistent use of `text-embedding-3-large` at 1024 dimensions throughout. This mistake requires deleting and rebuilding the entire vector store to recover.

See `.planning/research/PITFALLS.md` for integration gotchas, security mistakes (prompt injection via Sentinel data, logging raw API responses), performance traps, and the "looks done but isn't" checklist.

---

## Implications for Roadmap

The build order is dependency-driven with two natural parallel tracks that converge at the integration point. The existing PLAN.md phase structure (0 through 7) is architecturally correct — research confirms the sequence, not the timing.

### Phase 0: Azure Resource Setup and Content Filter Modification

**Rationale:** Blocks everything else. Content filter modification takes 1-3 business days; it must be submitted before any security data flows through the system. Azure resource provisioning (OpenAI deployments, workspace RBAC) is a hard prerequisite.
**Delivers:** Working Azure credentials, verified connectivity to Sentinel and OpenAI, content filter modification submitted.
**Avoids:** Content filter pitfall (Pitfall 1 from PITFALLS.md). This cannot be addressed retroactively without blocking the demo.
**Research flag:** No research needed — standard Azure provisioning with well-documented steps.

### Phase 1: Project Scaffolding and Configuration

**Rationale:** Foundation layer has no external dependencies and enables all subsequent phases to be built with proper structure. `config.py` must exist before any client can be constructed.
**Delivers:** `config.py` with validated env var loading, `pyproject.toml` with ruff/mypy/pytest config, project structure with `src/` and `tests/` directories, `.env.example`.
**Uses:** `python-dotenv`, `pyproject.toml` tooling from STACK.md.
**Research flag:** No research needed — standard Python project setup.

### Phase 2: Sentinel Data Access Layer

**Rationale:** The Sentinel client is the most constrained component (Azure API behavior, KQL dialect, throttling limits, partial result handling) and must be built and validated against real data before the orchestration layer depends on it. Parallel track with Phase 2b.
**Delivers:** `sentinel_client.py` with KQL template registry and Sentinel REST API calls; tested against live workspace; retry logic and `LogsQueryPartialResult` handling built in; field projection (`| project`) enforced in all templates.
**Features addressed:** T1 (incident querying), T2 (incident drill-down), T6 (alert querying), D4 (trend analysis), D5 (entity investigation).
**Avoids:** Log Analytics throttling (Pitfall 4), token budget overflow from verbose data (Pitfall 6).
**Research flag:** Needs validation — test actual KQL templates against the target workspace to confirm column names and data shapes. The workspace may have custom fields or retention limits not visible from documentation.

### Phase 2b: OpenAI Client and Tool Definitions (parallel with Phase 2)

**Rationale:** `openai_client.py`, `tools.py`, and `prompts.py` have no dependency on `sentinel_client.py`. Building them in parallel with Phase 2 keeps both tracks unblocked.
**Delivers:** `openai_client.py` with tool loop (MAX_TOOL_ROUNDS=5 guard), token budget system using tiktoken, conversation history management; `tools.py` with all tool definitions under 800 characters each; `prompts.py` with security-domain system prompt.
**Avoids:** Tool call infinite loops (Pitfall 2), strict mode / parallel calls conflict (Pitfall 3), tool description length limit (Pitfall 5).
**Research flag:** No research needed — patterns are well-documented and code examples are in ARCHITECTURE.md.

### Phase 3: Agentic Integration (Tool Loop + Dispatch)

**Rationale:** Convergence point for the two parallel tracks. `tool_handlers.py` wires `sentinel_client` to the tool loop; this is where end-to-end function calling is validated for the first time.
**Delivers:** `tool_handlers.py` dispatch table with error-wrapping for all Sentinel tools; end-to-end validated flow: natural language query -> tool selection -> KQL execution -> synthesized response; grounded, accurate responses with no hallucination (T4).
**Features addressed:** T1, T2, T3, T4, T6, D8 (reasoning explanation).
**Avoids:** All six critical pitfalls converge here for verification — run the "looks done but isn't" checklist from PITFALLS.md at end of this phase.
**Research flag:** No research needed — patterns are validated in ARCHITECTURE.md with working code examples.

### Phase 4: Vector Store and Knowledge Base

**Rationale:** Depends on `openai_client.py` (for embedding generation) and a working Sentinel client (for the ingestion data source). Builds the differentiating RAG capability.
**Delivers:** `vector_store.py` with ChromaDB persistent client using `get_or_create_collection()` (not `create_collection()`); ingestion script that embeds historical incidents as serialized natural language (not raw JSON); `playbooks/` directory seeded with investigation content; semantic search integrated into tool loop.
**Features addressed:** D1 (MITRE investigation guidance), D2 (historical pattern matching), D6 (playbook-guided response).
**Avoids:** ChromaDB embedding model mismatch (uses consistent `text-embedding-3-large` at 1024D throughout); duplicate ingestion handled via stable incident ID upserts.
**Research flag:** No research needed for ChromaDB setup. Content creation for playbooks (D6) needs SOC domain expertise from the team — this is the only gap research cannot fill.

### Phase 5: CLI Interface and UX Polish

**Rationale:** The display layer should be built last, once the data and orchestration layers are stable. `rich` formatting applied to known response structures.
**Delivers:** `main.py` with full chat loop; color-coded severity tables; loading indicators during tool execution (T10 sub-10s perceived latency via spinners); visible tool call display (D7); `/status`, `/clear`, `/quit` slash commands (T8, T9); source attribution in responses ("based on live Sentinel query" vs. "from knowledge base").
**Features addressed:** T5, T8, T9, T10, D7.
**Research flag:** No research needed — `rich` library usage is well-documented.

### Phase 6: Testing and Validation

**Rationale:** Dedicated phase for validation scenarios, not just unit tests. Integration tests against live Azure require the full stack to be complete.
**Delivers:** Unit tests for each `src/` module with mocked clients; integration tests marked with `@pytest.mark.integration` for live Azure scenarios; pytest coverage report; validation of all PLAN.md validation scenarios; "looks done but isn't" checklist verified.
**Research flag:** No research needed — standard pytest patterns.

### Phase 7: Demo Preparation

**Rationale:** The security posture summary (D3) and cost comparison narrative (D9) are deliberately deferred here because they require the full working system to demonstrate convincingly.
**Delivers:** Security posture summary tool (D3) showcasing parallel tool execution synthesized into executive briefing; demo script with scripted query sequence; cost comparison framing (D9); rehearsed fallback for any live connectivity issues.
**Features addressed:** D3, D9.
**Research flag:** No research needed — demo scripting is a team activity.

### Phase Ordering Rationale

- Phase 0 is non-negotiable first — content filter modification has a lead time that cannot be compressed.
- Phases 2 and 2b run in parallel because `sentinel_client.py` and `openai_client.py` have no cross-dependency; this is the key parallelization opportunity that keeps the 12-day timeline feasible.
- Phase 3 deliberately follows both parallel tracks — it is the integration point where the two tracks first touch.
- Phase 4 follows Phase 3 because embedding generation reuses `openai_client.py` and ingestion benefits from a validated Sentinel client.
- Phase 5 is intentionally last in the "building" phases — it is purely presentation and should not be built until the underlying data is stable.
- Phases 6 and 7 are sequential closes: validate, then demo.

### Research Flags

Phases needing deeper research or external validation during planning:

- **Phase 2 (Sentinel Data Access):** KQL column names, table schemas, and retention policies vary by workspace configuration. The team must run `search * | take 1` discovery queries against the actual workspace early to validate all KQL templates before the agentic layer depends on them.
- **Phase 4 (Vector Store — content):** Research cannot provide the investigation playbook content. This requires domain expertise from the SOC team. Playbook authoring is on the critical path for D6.
- **Phase 0 (Content filter):** The content filter modification request must be submitted and approved by Microsoft. Approval turnaround is typically 1-3 business days but is not guaranteed. If approval is delayed, the team needs a fallback: rephrase security queries to avoid trigger words, or demonstrate with sanitized sample data for the leadership demo.

Phases with well-documented patterns (no per-phase research needed):

- **Phase 1:** Standard Python project scaffolding.
- **Phase 2b:** Tool loop and token budgeting patterns are fully documented with working code in ARCHITECTURE.md.
- **Phase 3:** Dispatch table wiring is straightforward once both client libraries are working.
- **Phase 5:** `rich` library usage is well-documented.
- **Phase 6:** Standard pytest patterns.
- **Phase 7:** Demo scripting is a team activity, not a research problem.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI on 2026-02-16. All CLAUDE.md design decisions confirmed correct. No corrections needed to existing architecture decisions. |
| Features | MEDIUM-HIGH | Table stakes and differentiators based on stable SOC workflow patterns (HIGH confidence). Competitor feature comparison (Security Copilot, Chronicle) based on training data from mid-2025 (MEDIUM confidence — verify against current product docs before using in leadership demo narrative). |
| Architecture | HIGH | Tool loop pattern, dispatch table, KQL template registry, and token budgeting patterns verified against official Microsoft documentation updated 2026-02-10. Working code examples included in ARCHITECTURE.md. |
| Pitfalls | HIGH | Six critical pitfalls verified against official Azure OpenAI and Azure Monitor documentation (most updated late 2025/early 2026). Specific limits (5 concurrent queries, 1,024-char tool descriptions, strict mode / parallel calls constraint) are documented facts, not inferences. |

**Overall confidence:** HIGH

### Gaps to Address

- **Workspace-specific KQL schemas:** Column names and field availability in `SecurityIncident`, `SecurityAlert`, `SigninLogs`, etc. depend on the specific Sentinel workspace configuration and connected data sources. Run discovery queries against the target workspace in Phase 2 before finalizing KQL templates. Do not assume the standard schema applies without verification.

- **Content filter modification approval timeline:** The approval process is outside the team's control. If not approved before Phase 2, the team must test with synthetic security data and defer real-data validation. Flag this as a dependency risk in the roadmap.

- **SOC playbook content for ChromaDB:** D6 (playbook-guided response) requires actual investigation playbooks. These must be sourced from the SOC team or authored specifically for the POC. This is a content gap, not a technical gap. Schedule this alongside Phase 4 work.

- **Security Copilot competitor feature verification:** The feature comparison in FEATURES.md is based on training data from mid-2025. Before using it in the leadership demo narrative, verify current Security Copilot capabilities (SCU pricing, feature set) against Microsoft's current product documentation. The core build-vs-buy cost argument is valid; specific feature claims need verification.

- **Azure OpenAI endpoint format:** Integration gotchas research identified that resources created before August 2025 use the legacy endpoint format (requires `api_version` parameter) while newer resources use the `/openai/v1/` endpoint. Confirm the target Azure OpenAI resource's creation date and test the connection pattern in Phase 0 to avoid authentication surprises in Phase 2b.

---

## Sources

### Primary (HIGH confidence)

- [Azure OpenAI Function Calling — Official Microsoft Docs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/function-calling) (updated 2026-02-10) — verified tool loop pattern, parallel function calling, tool_choice parameter, 1,024-char description limit, strict mode constraint
- [Azure OpenAI Structured Outputs Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) (updated 2025-12-06) — verified strict mode / parallel_tool_calls incompatibility
- [Azure Monitor Query Client Library for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme) (azure-monitor-query v2.0.0, 2025-07-30) — verified LogsQueryClient API, partial result handling, batch queries, server_timeout
- [Azure Monitor Service Limits](https://learn.microsoft.com/en-us/azure/azure-monitor/fundamentals/service-limits) (updated 2025-12-17) — verified 5 concurrent queries per user, 200 req/30s, 500K rows, 10-min timeout
- [Microsoft Sentinel REST API Reference](https://learn.microsoft.com/en-us/rest/api/securityinsights/) — API version 2025-09-01
- [Azure OpenAI Quotas and Limits](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/quotas-limits) (updated 2026-01-14) — verified gpt-4o rate limits, 128 tool maximum, 2048 max messages
- PyPI package versions — openai 2.21.0, azure-monitor-query 2.0.0, azure-identity 1.25.2, chromadb 1.5.0, tiktoken 0.12.0, rich 14.3.2, pytest 9.0.2, ruff 0.15.1 — all verified 2026-02-16
- Project INITIAL-RESEARCH.md, PLAN.md, CLAUDE.md — confirmed all existing design decisions are architecturally correct

### Secondary (MEDIUM confidence)

- Training data on SOC analyst workflows, MITRE ATT&CK framework, SIEM operations — general patterns are stable; HIGH confidence for domain context
- Training data on Microsoft Security Copilot (GA April 2024) — feature comparison in FEATURES.md; verify current product docs before demo use
- CyberRAG paper (referenced in INITIAL-RESEARCH.md) — ~45% analyst triage time reduction with agentic RAG; supports project value proposition

### Tertiary (LOW confidence)

- Chronicle Security Operations and Splunk AI Assistant feature comparisons — based on training data; not used in roadmap decisions; verify if needed for competitive positioning

---

*Research completed: 2026-02-16*
*Ready for roadmap: yes*
