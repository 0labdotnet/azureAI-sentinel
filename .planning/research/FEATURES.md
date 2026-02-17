# Feature Landscape: Sentinel RAG Chatbot POC

**Domain:** Security SIEM chatbot / SOC natural language query assistant
**Researched:** 2026-02-16
**Confidence:** MEDIUM (training data + existing project research; no live web verification available)

## Audience Context

This POC serves two distinct audiences with different expectations:

1. **Leadership demo** -- needs to feel polished, deliver "wow" moments, and clearly demonstrate the build-vs-buy value proposition against Microsoft Security Copilot. Leaders care about speed, cost savings potential, and "could this replace our need for Security Copilot SCUs?"

2. **SOC analyst trial** -- needs to actually answer real questions faster than the current KQL-manual-query workflow. Analysts will judge on accuracy, response latency, and whether the tool understands security context. If the first three queries return garbage, they will never open it again.

The feature set must satisfy both audiences within a 12-day timeline.

---

## Table Stakes

Features users expect. Missing any of these = POC feels broken or incomplete.

| # | Feature | Why Expected | Complexity | Phase | Notes |
|---|---------|--------------|------------|-------|-------|
| T1 | **Natural language incident querying** | This IS the product. "Show me high-severity incidents from the last 24 hours" must work. | Med | 2-3 | KQL template + function calling. Core loop. |
| T2 | **Incident detail drill-down** | After seeing a list, analysts always ask "tell me more about incident X." Conversational follow-up is essential. | Med | 2-3 | Requires incident-by-ID lookup tool. |
| T3 | **Multi-turn conversation with context** | SOC investigation is inherently multi-turn: overview -> drill down -> ask about entities -> get recommendation. Stateless single-turn is useless. | Med | 3, 5 | Conversation history management with token budgeting. |
| T4 | **Accurate, grounded responses** | If the chatbot hallucinates incident numbers, severities, or timestamps, analysts will instantly distrust it. Every factual claim must come from tool call results. | High | 3 | System prompt engineering + always-cite-sources pattern. |
| T5 | **Formatted output (tables, color-coded severity)** | Raw JSON or wall-of-text is unreadable. Severity should be color-coded (red/orange/yellow). Incident lists should be tables. | Low | 5 | `rich` library handles this. Low effort, high polish. |
| T6 | **Alert querying and filtering** | Incidents are the primary object, but alerts are the underlying evidence. "What alerts triggered this incident?" is a natural follow-up. | Med | 2 | KQL against SecurityAlert table. |
| T7 | **Error handling with clear messages** | Azure API failures (auth, rate limits, timeouts) must produce helpful messages, not stack traces. | Low | 1-5 | Graceful error wrapping at each layer. |
| T8 | **Connection status and health check** | Analyst must be able to verify "is this thing actually connected to my Sentinel workspace?" before trusting results. | Low | 5 | `/status` command checking Azure connectivity. |
| T9 | **Session management (clear, quit)** | Basic CLI hygiene: `/clear` to reset context, `/quit` to exit. Without these, the tool feels unfinished. | Low | 5 | Trivial to implement. |
| T10 | **Sub-10-second response time for simple queries** | If it takes 30 seconds to list incidents, the speed value proposition is dead. KQL queries complete in 1-3 seconds; the LLM round-trip is the bottleneck. | Med | 3, 5 | Monitor and optimize. Loading indicators essential. |

---

## Differentiators

Features that create "wow" moments for leadership and make analysts say "this is actually useful." Not expected in a POC, but each one significantly raises perceived value.

| # | Feature | Value Proposition | Complexity | Phase | Notes |
|---|---------|-------------------|------------|-------|-------|
| D1 | **Investigation guidance with MITRE ATT&CK mapping** | After showing an incident, the chatbot recommends investigation steps mapped to MITRE techniques. This is what Security Copilot does and what makes junior analysts productive. | Med | 3-4 | System prompt + playbook retrieval from vector store. High demo impact. |
| D2 | **Historical pattern matching ("Have we seen this before?")** | Searches vector store for similar past incidents. Surfaces whether this is a recurring attack pattern or novel. This is the RAG value proposition -- enriching live data with historical context. | Med | 4 | ChromaDB semantic search. This is why we built the vector store. |
| D3 | **Security posture summary** | "Summarize today's security posture for a management briefing" -- aggregates multiple data sources into an executive-level summary. Perfect for the leadership demo. | Med | 3-4 | Parallel tool calls (incidents + alerts + trends), LLM synthesis. |
| D4 | **Alert trend analysis** | "How have alerts changed over the past 7 days?" with trend summarization. Shows the tool can do analytics, not just lookups. | Low | 2-3 | KQL summarize query + LLM narrative. Low effort, high demo value. |
| D5 | **Entity investigation ("Who is being targeted?")** | "What entities have been most attacked this week?" -- surfaces top-targeted users, IPs, hosts. Shows the tool understands security concepts beyond raw data. | Med | 2-3 | KQL entity extraction. Valuable for analyst workflow. |
| D6 | **Playbook-guided response** | "What's the response procedure for phishing?" retrieves investigation playbooks from the knowledge base. Directly helps junior analysts who don't know procedures. | Med | 4 | Requires seeding ChromaDB with playbook documents. Content creation effort. |
| D7 | **Parallel tool execution (visible)** | When the chatbot calls multiple tools simultaneously, show what it's doing: "Querying incidents... Checking alert trends... Searching knowledge base..." This makes the AI feel intelligent and transparent. | Low | 5 | Display tool call names during execution. Low effort, high perceived value. |
| D8 | **Explanation of reasoning** | "I searched for high-severity incidents in the last 24 hours and found 3. I also checked the knowledge base for similar patterns..." Makes the AI trustworthy by showing its work. | Low | 3 | System prompt instruction to explain which tools were used and why. |
| D9 | **Cost comparison framing in demo** | Not a feature per se, but the demo script should highlight: "This query would have taken 5 minutes of KQL writing. Security Copilot costs $X/SCU. This POC runs on pay-as-you-go Azure OpenAI at pennies per query." | Low | 7 | Demo preparation. Frame the build-vs-buy narrative. |

---

## Anti-Features

Features to explicitly NOT build. Each one is tempting but would waste time, add risk, or undermine the POC's value proposition.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|--------------|-----------|-------------------|
| A1 | **Freeform KQL generation** | LLMs produce syntactically valid but semantically wrong KQL. A wrong query that returns results is worse than an error -- it gives false confidence. This is a known, documented failure mode. | Use pre-defined KQL templates with parameter substitution. The LLM picks which template and fills parameters. Safe, reliable, auditable. |
| A2 | **Write operations (close incident, assign, comment)** | Violates the read-only safety constraint. One accidental bulk-close of incidents during a demo would be catastrophic. Write operations require a completely different trust/approval model. | Explicitly exclude write tools. System prompt reinforces read-only role. Document write operations as a post-POC production feature. |
| A3 | **Web UI or API server** | Doubles the scope. A web UI requires auth, session management, deployment, CORS, and 10x the testing surface. The CLI is the demo; it is sufficient to prove the concept. | CLI with `rich` formatting. If the POC succeeds, web UI is Phase 1 of production. |
| A4 | **Real-time streaming responses** | Streaming adds complexity (async generators, partial rendering) for marginal UX gain in a CLI. Standard request/response with a loading indicator is fine for a POC. | Show a spinner/progress indicator during API calls. Streaming is a production enhancement. |
| A5 | **Multi-workspace or multi-tenant support** | Multiplies configuration, testing, and edge cases. POC targets one workspace. | Single workspace config. Document multi-workspace as production scope. |
| A6 | **Automated continuous data ingestion** | Building a real-time pipeline (Event Grid, Functions, scheduled jobs) is production infrastructure work. For a POC, a one-time or on-demand ingestion script is sufficient. | Manual `/refresh` command or startup ingestion script. Production uses Azure Functions timer triggers. |
| A7 | **Custom fine-tuned models** | Fine-tuning requires training data collection, model training, evaluation, and deployment. gpt-4o with good prompting and function calling is more than sufficient for a POC. | Invest time in system prompt engineering instead. Better ROI for a 12-day timeline. |
| A8 | **Comprehensive RBAC / per-user access control** | The POC runs locally with a single service principal. Building per-user auth, token exchange, and ACLs on the vector store is production work. | Single service principal with Sentinel Reader permissions. Document RBAC as production requirement. |
| A9 | **Integration with ticketing systems (ServiceNow, Jira)** | Out of scope for proving the Sentinel query concept. Adds external dependencies and complexity. | Focus purely on Sentinel data retrieval and analysis. |
| A10 | **NL-to-KQL with query preview/edit** | Tempting "power user" feature, but freeform KQL generation is unreliable (see A1), and building a preview/edit/approve workflow is significant UI work for a CLI. | Expand the set of pre-defined KQL templates to cover more query patterns. If a user asks something no template covers, say so honestly. |

---

## Feature Dependencies

```
T1 (Incident querying) --> T2 (Incident drill-down) -- drill-down requires list first
T1 (Incident querying) --> T3 (Multi-turn) -- multi-turn requires at least one working query
T1 + T6 (Incidents + Alerts) --> D3 (Security posture summary) -- summary aggregates multiple data types
T1 + T6 --> D5 (Entity investigation) -- entities come from incidents and alerts
T3 (Multi-turn) --> D1 (Investigation guidance) -- guidance is a follow-up to "tell me about incident X"
D2 (Historical matching) --> D6 (Playbook guidance) -- both require populated vector store
T5 (Formatted output) --> D7 (Visible tool execution) -- tool display uses the formatting layer
T4 (Grounded responses) --> D8 (Explain reasoning) -- both driven by system prompt design

Phase dependency chain:
  Sentinel client (T1, T2, T6) --> OpenAI integration (T3, T4) --> Vector store (D1, D2, D6) --> CLI (T5, D7) --> Polish (D3, D8, D9)
```

---

## Competitor Feature Matrix

How this POC compares to the "buy" option and other tools. Based on training data knowledge of Security Copilot and related products (MEDIUM confidence -- features may have changed since training cutoff).

| Feature | This POC | Security Copilot | Chronicle SecOps (Google) |
|---------|----------|-----------------|--------------------------|
| Natural language incident query | Yes | Yes | Yes |
| Multi-turn conversation | Yes | Yes | Yes |
| MITRE ATT&CK mapping | Yes (via prompting + playbooks) | Yes (native) | Yes (native) |
| Investigation guidance | Yes (playbook retrieval) | Yes (built-in) | Yes (built-in) |
| Historical pattern matching | Yes (ChromaDB RAG) | Limited (session-based) | Yes (Chronicle data lake) |
| KQL/query generation | No (templates only) | Yes (generates KQL) | Yes (generates UDM search) |
| Write operations (triage, assign) | No (read-only) | Yes | Yes |
| Multi-source correlation | Sentinel only | Cross-Microsoft stack | Cross-Google stack |
| Custom data source integration | Possible (extensible) | Plugin ecosystem | Limited |
| Cost model | Pay-as-you-go (~$0.01-0.05/query) | SCU-based consumption ($4/SCU-hour) | Bundled with Chronicle |
| Data sovereignty / transparency | Full control | Microsoft-managed | Google-managed |
| Customizable prompts/behavior | Full control | Limited | Limited |

**POC competitive advantages:** Cost transparency, full prompt/retrieval customization, ability to integrate non-Microsoft data sources, complete audit trail of every LLM interaction.

**POC competitive disadvantages:** No write operations, single SIEM source, no cross-product correlation, no built-in threat intelligence feeds.

---

## MVP Recommendation

For the 12-day POC timeline, prioritize features in this order:

### Must Ship (Week 1)
1. **T1** -- Natural language incident querying (the core feature)
2. **T2** -- Incident detail drill-down (makes conversations useful)
3. **T6** -- Alert querying (incidents alone are insufficient)
4. **T3** -- Multi-turn conversation (investigation is multi-step)
5. **T4** -- Grounded, accurate responses (trust is everything)
6. **T5** -- Formatted output with severity coloring (polish for demos)
7. **T7** -- Error handling (broken errors kill demos)

### Should Ship (Week 2, first half)
8. **D1** -- Investigation guidance with MITRE mapping (differentiator, high demo impact)
9. **D2** -- Historical pattern matching (the RAG value proposition)
10. **D4** -- Alert trend analysis (low effort, high demo value)
11. **D5** -- Entity investigation (practical analyst feature)
12. **D7** -- Visible parallel tool execution (makes AI feel smart)

### Demo Polish (Week 2, second half)
13. **D3** -- Security posture summary (perfect demo closer)
14. **D8** -- Explanation of reasoning (transparency)
15. **T8** -- Connection status check
16. **T9** -- Session management commands
17. **D6** -- Playbook-guided response (requires content seeding)
18. **D9** -- Cost comparison framing in demo script

### Defer to Post-POC
- **T10** -- Response time optimization (measure first, optimize only if needed)
- Everything in the Anti-Features list

---

## Features Mapped to Existing Plan Phases

The existing PLAN.md phases align well with the feature priority above:

| Plan Phase | Features Addressed | Notes |
|------------|-------------------|-------|
| Phase 0 (Azure Setup) | Prerequisites for all features | No features directly, but blocks everything |
| Phase 1 (Scaffolding) | T7 (error handling foundation) | Config, project structure |
| Phase 2 (Sentinel Client) | T1, T2, T6, D4, D5 | Core data access. Most table-stakes features. |
| Phase 3 (OpenAI Integration) | T3, T4, D8 | Function calling, system prompt, grounding |
| Phase 4 (Vector Store) | D1, D2, D6 | Historical context, playbooks. Key differentiators. |
| Phase 5 (CLI Interface) | T5, T8, T9, T10, D7 | Formatting, UX polish, visible tool execution |
| Phase 6 (Testing) | Validates all features | Validation scenarios from PLAN.md |
| Phase 7 (Demo Prep) | D3, D9 | Summary feature, demo script, narrative |

---

## Sources

- INITIAL-RESEARCH.md (project repository) -- architecture decisions, tool definitions, KQL tables, reference projects
- PLAN.md (project repository) -- phase structure, validation scenarios, production considerations
- CLAUDE.md (project repository) -- design decisions, constraints
- Training data on Microsoft Security Copilot (GA April 2024, embedded experiences, standalone portal) -- MEDIUM confidence, features may have evolved
- Training data on SOC analyst workflows, MITRE ATT&CK framework, SIEM operations -- HIGH confidence for general patterns, these are stable domain concepts
- Training data on Chronicle Security Operations (Google), Splunk AI Assistant -- LOW confidence for current feature sets
- CyberRAG paper (referenced in INITIAL-RESEARCH.md) -- validated ~45% analyst triage time reduction with agentic RAG approach

**Confidence note:** Web search and web fetch were unavailable during this research session. Competitor feature comparisons are based on training data (cutoff ~mid-2025) and should be verified against current product documentation before using in the leadership demo narrative. The feature categorization (table stakes vs. differentiators) is based on stable SOC workflow patterns and is HIGH confidence.
