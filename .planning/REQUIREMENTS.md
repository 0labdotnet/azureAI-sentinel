# Requirements: Sentinel RAG Chatbot POC

**Defined:** 2026-02-16
**Core Value:** SOC analysts can get answers about their security environment in seconds using plain English — no KQL knowledge required — with live data grounded in real Sentinel incidents and enriched by historical context.

## v1 Requirements

Requirements for the POC release. Each maps to exactly one roadmap phase.

### Sentinel Querying

- [x] **QUERY-01**: User can ask natural language questions about security incidents and receive accurate results from Sentinel (e.g., "Show me high-severity incidents from the last 24 hours")
- [x] **QUERY-02**: User can drill down into a specific incident by number to see detailed information including related alerts and entities
- [x] **QUERY-03**: User can query security alerts filtered by severity and time range
- [ ] **QUERY-04**: User can ask about alert trends over the past 7 days and receive a summarized analysis
- [ ] **QUERY-05**: User can ask which entities (users, IPs, hosts) have been most targeted and receive a ranked analysis

### AI Orchestration

- [ ] **ORCH-01**: User can have multi-turn conversations where the chatbot remembers prior context (e.g., "tell me more about that incident" after an incident list)
- [ ] **ORCH-02**: All factual claims in chatbot responses are grounded in tool call results — the chatbot never fabricates incident numbers, severities, or timestamps
- [ ] **ORCH-03**: Chatbot explains its reasoning by describing which tools it used and what data it found before answering

### Knowledge Base

- [ ] **KB-01**: User can ask for investigation guidance for a specific incident type and receive MITRE ATT&CK-mapped recommendations retrieved from the knowledge base
- [ ] **KB-02**: User can ask "have we seen this type of attack before?" and the chatbot searches historical incidents for similar patterns
- [ ] **KB-03**: User can ask about investigation procedures (e.g., "what's the response procedure for phishing?") and receive playbook-based guidance from the knowledge base

### CLI Experience

- [ ] **CLI-01**: Incident lists are displayed in formatted tables with color-coded severity (red for High, orange for Medium, etc.)
- [ ] **CLI-02**: Azure API errors (auth failures, rate limits, timeouts) produce clear, actionable error messages — never raw stack traces
- [ ] **CLI-03**: User can run `/status` to verify connectivity to Azure OpenAI and Sentinel
- [ ] **CLI-04**: User can run `/clear` to reset conversation history and `/quit` or `/exit` to end the session
- [ ] **CLI-05**: During tool execution, the chatbot shows which tools are running (e.g., "Querying incidents... Searching knowledge base...") so the user sees progress
- [ ] **CLI-06**: User can ask for a security posture summary and receive an executive-level briefing synthesized from multiple data sources (incidents, alerts, trends)

### Demo Preparation

- [ ] **DEMO-01**: A scripted demo walkthrough exists covering: active threats, deep dive, historical context, trend analysis, and security posture summary
- [ ] **DEMO-02**: Demo narrative includes build-vs-buy cost comparison framing against Security Copilot

## v2 Requirements

Deferred to post-POC. Tracked but not in current roadmap.

### Advanced Querying

- **QUERY-06**: User can query across multiple Sentinel workspaces
- **QUERY-07**: User can query threat intelligence indicators (ThreatIntelIndicators table)
- **QUERY-08**: User can query sign-in logs with natural language filtering

### Operations

- **OPS-01**: User can close or reassign incidents via the chatbot (write operations)
- **OPS-02**: User can create investigation notes on incidents
- **OPS-03**: Chatbot integrates with ticketing systems (ServiceNow, Jira)

### Infrastructure

- **INFRA-01**: Replace ChromaDB with Azure AI Search for production-grade vector storage
- **INFRA-02**: Automated continuous data ingestion pipeline (Azure Functions timer trigger)
- **INFRA-03**: Web UI or API server for browser-based access
- **INFRA-04**: Per-user RBAC with Entra ID authentication

### AI Enhancements

- **AI-01**: Streaming responses for real-time token display
- **AI-02**: Freeform KQL generation with preview/approve workflow
- **AI-03**: Multi-model routing (cheaper model for simple queries, stronger for complex)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Freeform KQL generation | LLMs produce semantically wrong KQL; pre-defined templates are safer and more reliable |
| Write operations to Sentinel | Violates read-only safety constraint; catastrophic risk if triggered accidentally in demo |
| Web UI or API server | Doubles scope; CLI with `rich` is sufficient to prove the concept |
| Streaming responses | Marginal UX gain in CLI; spinner is sufficient for POC |
| Multi-workspace / multi-tenant | Multiplies configuration and testing; single workspace for POC |
| Automated data ingestion pipeline | Production infrastructure; manual/on-demand ingestion sufficient for POC |
| Fine-tuned models | gpt-4o with prompting and function calling is sufficient; fine-tuning is production scope |
| LangChain or orchestration frameworks | Direct OpenAI SDK is simpler, more transparent, and easier to debug for demos |
| Integration with ticketing systems | Out of scope for proving the Sentinel query concept |

## Traceability

Each v1 requirement maps to exactly one phase. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| QUERY-01 | Phase 2 | Complete |
| QUERY-02 | Phase 2 | Complete |
| QUERY-03 | Phase 2 | Complete |
| QUERY-04 | Phase 2 | Pending |
| QUERY-05 | Phase 2 | Pending |
| ORCH-01 | Phase 3 | Pending |
| ORCH-02 | Phase 3 | Pending |
| ORCH-03 | Phase 3 | Pending |
| KB-01 | Phase 4 | Pending |
| KB-02 | Phase 4 | Pending |
| KB-03 | Phase 4 | Pending |
| CLI-01 | Phase 5 | Pending |
| CLI-02 | Phase 5 | Pending |
| CLI-03 | Phase 5 | Pending |
| CLI-04 | Phase 5 | Pending |
| CLI-05 | Phase 5 | Pending |
| CLI-06 | Phase 5 | Pending |
| DEMO-01 | Phase 6 | Pending |
| DEMO-02 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0

---
*Requirements defined: 2026-02-16*
*Last updated: 2026-02-17 after roadmap creation (one-to-one phase mappings)*
