# Roadmap: Sentinel RAG Chatbot POC

## Overview

This roadmap delivers a POC command-line chatbot that gives SOC analysts natural language access to Microsoft Sentinel data. The build follows a dependency-driven sequence: Azure resource provisioning (which has a lead time for content filter approval) unblocks the Sentinel data access layer, which feeds into the AI orchestration integration point, which enables the knowledge base RAG layer. CLI polish is applied once the underlying data and AI layers are stable, and demo preparation caps the project with a scripted walkthrough for leadership.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Azure resource provisioning, content filter modification, project scaffolding, and config validation
- [x] **Phase 2: Sentinel Data Access** - KQL template registry and Sentinel client with live data queries for incidents, alerts, trends, and entities
- [ ] **Phase 3: AI Orchestration & Integration** - OpenAI tool loop, tool dispatch, multi-turn conversation, grounded responses, and end-to-end natural language querying
- [ ] **Phase 4: Knowledge Base** - ChromaDB vector store with historical incident search, MITRE ATT&CK investigation guidance, and playbook retrieval
- [ ] **Phase 5: CLI Experience & Polish** - Rich formatted output, color-coded severity tables, progress indicators, slash commands, error handling, and security posture summary
- [ ] **Phase 6: Demo Preparation** - Scripted demo walkthrough with build-vs-buy cost comparison narrative

## Phase Details

### Phase 1: Foundation
**Goal**: Azure resources are provisioned with verified connectivity, content filter modification is submitted, and the Python project is scaffolded with validated configuration loading
**Depends on**: Nothing (first phase)
**Requirements**: None (infrastructure prerequisite that unblocks all v1 requirements)
**Success Criteria** (what must be TRUE):
  1. Running `python -m src.config` loads and validates all required environment variables from `.env` without errors
  2. Azure OpenAI endpoint responds to a test chat completion request using the provisioned gpt-4o deployment
  3. Azure Monitor `LogsQueryClient` successfully executes a simple KQL query (`SecurityIncident | take 1`) against the Sentinel workspace
  4. Content filter modification request has been submitted in Azure AI Foundry (approval may be pending)
  5. `pytest` discovers and runs test files from the `tests/` directory with the project structure intact
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md -- Azure resource provisioning, content filter, .env setup
- [x] 01-02-PLAN.md -- Project scaffolding, config module, tests, mock fixtures

### Phase 2: Sentinel Data Access
**Goal**: The Sentinel client can execute all pre-defined KQL query templates and return structured, field-projected results from live Sentinel data
**Depends on**: Phase 1
**Requirements**: QUERY-01, QUERY-02, QUERY-03, QUERY-04, QUERY-05
**Success Criteria** (what must be TRUE):
  1. `sentinel_client.py` can query security incidents filtered by severity and time range, returning only projected fields (not full verbose rows)
  2. `sentinel_client.py` can retrieve detailed information for a specific incident by number, including related alerts and entities
  3. `sentinel_client.py` can query security alerts filtered by severity and time range
  4. `sentinel_client.py` can return alert trend data over a configurable time period and entity frequency rankings
  5. All queries handle partial results, timeouts, and HTTP 429 throttling with retry logic
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md -- Data models, KQL template registry, projections, and SentinelClient with incident/alert queries
- [x] 02-02-PLAN.md -- Trend/entity queries, SentinelClient extension, and live data verification

### Phase 3: AI Orchestration & Integration
**Goal**: Users can have multi-turn natural language conversations that invoke Sentinel tools and receive grounded, accurate responses with reasoning transparency
**Depends on**: Phase 1, Phase 2
**Requirements**: ORCH-01, ORCH-02, ORCH-03
**Success Criteria** (what must be TRUE):
  1. User can ask a natural language question (e.g., "show me high severity incidents from the last 24 hours"), the chatbot selects the correct tool, executes the KQL query, and returns an accurate synthesized answer
  2. User can have a multi-turn conversation where the chatbot remembers prior context (e.g., "tell me more about that incident" after listing incidents)
  3. All factual claims in responses (incident numbers, severities, timestamps) are traceable to tool call results with no fabricated data
  4. Chatbot explains which tools it used and what data it found before presenting its answer
  5. The tool loop terminates after MAX_TOOL_ROUNDS (5) iterations and never enters an infinite loop
**Plans**: TBD

Plans:
- [ ] 03-01: OpenAI client with tool loop, token budget, and conversation history
- [ ] 03-02: Tool definitions, dispatch table, and end-to-end integration

### Phase 4: Knowledge Base
**Goal**: Users can query historical incidents and investigation playbooks through the ChromaDB vector store, receiving MITRE ATT&CK-mapped guidance and pattern matching results
**Depends on**: Phase 3
**Requirements**: KB-01, KB-02, KB-03
**Success Criteria** (what must be TRUE):
  1. User can ask for investigation guidance for a specific incident type and receive recommendations mapped to MITRE ATT&CK techniques
  2. User can ask "have we seen this type of attack before?" and receive semantically matched historical incidents from the knowledge base
  3. User can ask about response procedures (e.g., "what's the response procedure for phishing?") and receive playbook-based guidance
  4. Embeddings use text-embedding-3-large at 1024 dimensions consistently for both ingestion and retrieval (no model mismatch)
**Plans**: TBD

Plans:
- [ ] 04-01: ChromaDB vector store, embedding pipeline, and knowledge base content
- [ ] 04-02: Semantic search tools integrated into the tool loop

### Phase 5: CLI Experience & Polish
**Goal**: The chatbot presents a polished, professional terminal interface with formatted output, progress feedback, error handling, slash commands, and an executive security posture summary
**Depends on**: Phase 3, Phase 4
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. Incident lists display in formatted tables with color-coded severity (red for High, orange for Medium, yellow for Low, green for Informational)
  2. Azure API errors (auth failures, rate limits, timeouts) produce clear, actionable error messages -- never raw stack traces or unhandled exceptions
  3. User can run `/status` to verify connectivity to Azure OpenAI and Sentinel, `/clear` to reset conversation, and `/quit` or `/exit` to end the session
  4. During tool execution, the chatbot shows which tools are running (e.g., "Querying incidents... Searching knowledge base...") so the user sees progress
  5. User can ask for a security posture summary and receive an executive-level briefing synthesized from multiple data sources (incidents, alerts, trends) via parallel tool calls
**Plans**: TBD

Plans:
- [ ] 05-01: Rich formatted output, severity tables, and progress indicators
- [ ] 05-02: Slash commands, error handling, and security posture summary

### Phase 6: Demo Preparation
**Goal**: A complete, rehearsable demo script exists that walks through the chatbot's capabilities with a compelling build-vs-buy narrative against Security Copilot
**Depends on**: Phase 5
**Requirements**: DEMO-01, DEMO-02
**Success Criteria** (what must be TRUE):
  1. A scripted demo walkthrough exists covering: active threats query, incident deep dive, historical context lookup, trend analysis, and security posture summary
  2. The demo narrative includes build-vs-buy cost comparison framing against Microsoft Security Copilot (SCU pricing vs. Azure OpenAI token costs)
  3. The demo can run end-to-end without errors against the Sentinel training lab data
**Plans**: TBD

Plans:
- [ ] 06-01: Demo script, walkthrough sequence, and fallback plan

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-02-18 |
| 2. Sentinel Data Access | 2/2 | Complete | 2026-02-18 |
| 3. AI Orchestration & Integration | 0/2 | Not started | - |
| 4. Knowledge Base | 0/2 | Not started | - |
| 5. CLI Experience & Polish | 0/2 | Not started | - |
| 6. Demo Preparation | 0/1 | Not started | - |
