# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

POC command-line Python chatbot that lets SOC teams query Microsoft Sentinel SIEM data using natural language via Azure OpenAI. Uses a **hybrid agentic RAG** architecture: function calling for live Sentinel data + ChromaDB vector store for historical context and playbooks.

**Status:** Pre-implementation. See PLAN.md for the phased build plan and INITIAL-RESEARCH.md for technical research.

## Build and Run Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run the chatbot
python -m src.main

# Run all tests
pytest

# Run a single test file
pytest tests/test_sentinel_client.py

# Run with verbose output
pytest -v
```

## Architecture

### Planned Project Structure

```
src/
├── main.py               # CLI entry point and chat loop (rich-formatted output)
├── config.py             # Env var loading/validation via python-dotenv
├── sentinel_client.py    # KQL queries via azure-monitor-query LogsQueryClient
├── openai_client.py      # Azure OpenAI chat (gpt-4o) and embeddings (text-embedding-3-large)
├── tools.py              # OpenAI function calling tool definitions
├── tool_handlers.py      # Dispatches tool calls to sentinel_client and vector_store
├── vector_store.py       # ChromaDB persistent client for historical incidents/playbooks
└── prompts.py            # System prompts and prompt templates
```

### Key Data Flow

1. User types natural language query in CLI
2. Query sent to Azure OpenAI with conversation history + tool definitions
3. LLM decides which tools to call (may call multiple in parallel)
4. Tool handler dispatches to Sentinel API (live data) or ChromaDB (historical)
5. Results sent back to LLM for synthesis
6. Formatted response displayed via `rich` library

### Critical Design Decisions

- **No LangChain** — uses OpenAI SDK directly with function calling for simplicity and transparency
- **Pre-defined KQL templates only** — no freeform KQL generation (LLMs produce buggy KQL)
- **`azure-monitor-query` for KQL** — the `azure-mgmt-securityinsight` package is stale (last released July 2022), avoid it
- **`tools` parameter, not `functions`** — the `functions`/`function_call` API is deprecated
- **openai v2.x** — project targets the v2.x SDK, not v1.x
- **text-embedding-3-large at 1024 dimensions** — truncated from 3072 for best quality/cost ratio
- **All LLM-exposed tools are read-only** — no write operations to Sentinel

## Azure Authentication

Uses `DefaultAzureCredential` from `azure-identity` which supports both:
- Local dev: `az login` (AzureCliCredential)
- Service principal: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` env vars

Required roles: Microsoft Sentinel Reader, Log Analytics Reader, Cognitive Services OpenAI User.

## Environment Variables

All config loaded from `.env` file — see INITIAL-RESEARCH.md section 9.6 for the full list. Key variables:
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` — OpenAI resource
- `SENTINEL_WORKSPACE_ID` — Log Analytics workspace GUID
- `AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large`

## Key Sentinel KQL Tables

`SecurityIncident`, `SecurityAlert`, `ThreatIntelIndicators`, `SigninLogs`, `CommonSecurityLog` — queried via `LogsQueryClient.query_workspace()`.
