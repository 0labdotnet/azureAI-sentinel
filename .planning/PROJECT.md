# Sentinel RAG Chatbot POC

## What This Is

A command-line Python chatbot that lets SOC teams query Microsoft Sentinel SIEM data using natural language via Azure OpenAI. Uses a hybrid agentic RAG architecture: function calling for live Sentinel data (incidents, alerts, sign-in logs) plus a ChromaDB vector store for historical context and investigation playbooks. Built as a POC to prove feasibility and demonstrate value as a "build" alternative to Microsoft Security Copilot.

## Core Value

SOC analysts can get answers about their security environment in seconds using plain English — no KQL knowledge required — with live data grounded in real Sentinel incidents and enriched by historical context.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

- [ ] CLI chat interface with natural language querying of Sentinel data
- [ ] Azure OpenAI function calling for live Sentinel queries (incidents, alerts, entities)
- [ ] Pre-defined KQL templates (not freeform KQL generation) for safe, reliable queries
- [ ] ChromaDB vector store for historical incident context and playbook retrieval
- [ ] Multi-turn conversation with context preservation
- [ ] Rich formatted terminal output (severity color-coding, tables, markdown)
- [ ] Investigation guidance based on MITRE ATT&CK framework
- [ ] Read-only access to Sentinel (no write operations exposed to LLM)
- [ ] Demo-ready with scripted walkthrough for leadership presentation
- [ ] Usable by junior analysts who don't know KQL

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Production deployment — POC runs locally only
- LangChain or other orchestration frameworks — using OpenAI SDK directly for simplicity and transparency
- Freeform KQL generation — LLMs produce buggy KQL; using pre-defined templates instead
- Write operations to Sentinel — all tools are read-only for safety
- Multi-tenancy / multi-workspace — single workspace for POC
- Azure AI Search — using ChromaDB locally; migrate to AI Search for production
- Real-time streaming responses — standard request/response for POC simplicity
- Web UI / API server — CLI only for POC

## Context

- The research phase is complete (see INITIAL-RESEARCH.md) with validated architecture decisions
- A detailed phase-by-phase build plan exists (see PLAN.md) covering Phases 0-7
- Azure resources (OpenAI, Sentinel workspace) are NOT yet provisioned — Phase 0 is real work
- Will use Sentinel Training Lab or sample data connectors (not production data)
- gpt-4o is the target chat model; text-embedding-3-large at 1024 dimensions for embeddings
- The `azure-mgmt-securityinsight` package is stale (July 2022) — using `azure-monitor-query` and direct REST calls instead
- Target audience: both leadership demo and hands-on SOC analyst trial
- Three value propositions: speed (seconds vs. minutes), context (historical enrichment + investigation guidance), accessibility (no KQL needed)

## Constraints

- **Timeline**: ~12 days (end of February 2026) to working POC
- **Tech stack**: Python 3.10+, Azure OpenAI (gpt-4o), ChromaDB, azure-monitor-query, openai v2.x SDK
- **No LangChain**: Direct OpenAI SDK for simplicity and transparency
- **No freeform KQL**: Pre-defined templates only (LLM-generated KQL is unreliable)
- **Read-only**: All LLM-exposed tools must be read-only
- **Data**: Sample/training data (Sentinel Training Lab), not production data
- **Azure region**: Must verify gpt-4o availability before provisioning (East US, East US 2, West US 2, Sweden Central recommended)

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| No LangChain — direct OpenAI SDK | Simplicity, transparency, easy to understand for demos | — Pending |
| Pre-defined KQL templates only | LLMs produce buggy KQL; templates are safe and reliable | — Pending |
| ChromaDB for vector store | Zero-config local persistence; fastest path to working POC | — Pending |
| gpt-4o as chat model | Proven, widely available, 128K context sufficient | — Pending |
| text-embedding-3-large at 1024D | Best quality/cost ratio (within 1-2% of full 3072D) | — Pending |
| azure-monitor-query for KQL | Avoids stale azure-mgmt-securityinsight package | — Pending |
| Hybrid agentic RAG architecture | Live data changes too fast for pure embedding; function calling for live + vectors for historical | — Pending |

---
*Last updated: 2026-02-16 after initialization*
