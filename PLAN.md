# Project Plan: Azure Sentinel RAG Chatbot POC

> **Goal:** Build a command-line Python chatbot that allows SOC teams to query Microsoft Sentinel SIEM data using natural language via Azure OpenAI, proving the integration is feasible and provides meaningful value.

---

## Phase 0: Azure Resource Setup and Configuration

### 0.1 Azure OpenAI Resource

- [ ] Create or identify an existing Azure OpenAI resource in a supported region (East US, East US 2, West US 2, or Sweden Central recommended for gpt-4o availability)
- [ ] Deploy the **gpt-4o** model (version 2024-11-20 or later) — name the deployment `gpt-4o`
- [ ] Deploy the **text-embedding-3-large** model — name the deployment `text-embedding-3-large`
- [ ] Note the endpoint URL and generate an API key (or configure Entra ID token-based auth)

### 0.2 Microsoft Sentinel Workspace

- [ ] Confirm an active Microsoft Sentinel workspace exists with real or sample incident/alert data
- [ ] Note the Log Analytics **Workspace ID** (GUID), **Subscription ID**, **Resource Group**, and **Workspace Name**
- [ ] If no incidents exist, enable sample data connectors or create test analytics rules that generate alerts

### 0.3 Azure AD App Registration (Service Principal)

- [ ] Create an App Registration in Azure AD (Entra ID)
- [ ] Generate a client secret and note the **Tenant ID**, **Client ID**, and **Client Secret**
- [ ] Assign the following roles:
  - **Microsoft Sentinel Reader** — on the Sentinel workspace resource group
  - **Log Analytics Reader** — on the Log Analytics workspace
  - **Cognitive Services OpenAI User** — on the Azure OpenAI resource
- [ ] (Optional) Grant Microsoft Graph API permissions: `SecurityIncident.Read.All`, `SecurityAlert.Read.All`

### 0.4 Local Environment

- [ ] Install Python 3.10+
- [ ] Install Azure CLI and authenticate (`az login`)
- [ ] Create a `.env` file with all required environment variables (see INITIAL-RESEARCH.md section 9.6)
- [ ] Add `.env` to `.gitignore`

**Deliverable:** All Azure resources provisioned, service principal configured, local environment ready.

---

## Phase 1: Project Scaffolding and Core Infrastructure

### 1.1 Project Structure

Create the following directory layout:

```
azureAI-sentinel/
├── .env.example              # Template for environment variables (no secrets)
├── .gitignore
├── requirements.txt
├── README.md
├── INITIAL-RESEARCH.md
├── PLAN.md
├── src/
│   ├── __init__.py
│   ├── main.py               # CLI entry point and chat loop
│   ├── config.py             # Environment variable loading and validation
│   ├── sentinel_client.py    # Sentinel API and KQL query functions
│   ├── openai_client.py      # Azure OpenAI chat and embedding functions
│   ├── tools.py              # Tool definitions for function calling
│   ├── tool_handlers.py      # Tool execution logic (dispatches to sentinel_client)
│   ├── vector_store.py       # ChromaDB vector store operations
│   └── prompts.py            # System prompts and prompt templates
└── data/
    └── chroma_db/            # Local ChromaDB persistent storage (gitignored)
```

### 1.2 Dependencies Setup

- [ ] Create `requirements.txt` with pinned versions
- [ ] Create `.env.example` with all required variable names (no values)
- [ ] Create `.gitignore` (exclude `.env`, `data/chroma_db/`, `__pycache__/`, `.venv/`)
- [ ] Set up virtual environment and install dependencies

### 1.3 Configuration Module (`config.py`)

- [ ] Load environment variables from `.env` using `python-dotenv`
- [ ] Validate all required variables are present on startup
- [ ] Provide clear error messages for missing configuration

**Deliverable:** Project skeleton with all dependencies installed and configuration loading.

---

## Phase 2: Sentinel Data Access Layer

### 2.1 KQL Query Client (`sentinel_client.py`)

- [ ] Implement `SentinelClient` class using `azure-monitor-query` `LogsQueryClient`
- [ ] Implement method: `query_incidents(severity, status, time_range_hours, max_results)` — runs KQL against `SecurityIncident` table
- [ ] Implement method: `query_alerts(time_range_hours, severity, max_results)` — runs KQL against `SecurityAlert` table
- [ ] Implement method: `get_incident_details(incident_number)` — fetches a specific incident with related alerts via KQL join
- [ ] Implement method: `get_alert_trend(days)` — returns alert counts by severity over time
- [ ] Implement method: `get_top_attacked_entities(time_range_hours)` — returns most-targeted entities
- [ ] Implement method: `run_custom_kql(query_name, params)` — executes a predefined KQL template with parameter substitution
- [ ] Handle pagination, error handling, and timeouts
- [ ] Format query results as structured dictionaries suitable for LLM consumption

### 2.2 Predefined KQL Query Templates

Create a set of safe, parameterized KQL templates:

```
high_severity_incidents    — SecurityIncident | where Severity == "High" | ...
active_incidents           — SecurityIncident | where Status == "Active" | ...
incident_timeline          — SecurityIncident | summarize count() by bin(CreatedTime, 1h) | ...
alert_summary_by_severity  — SecurityAlert | summarize count() by AlertSeverity | ...
top_attacked_entities      — SecurityAlert | summarize count() by Entities | ...
failed_signins_by_ip       — SigninLogs | where ResultType != 0 | summarize count() by IPAddress | ...
```

### 2.3 Validation and Testing

- [ ] Test each query method against the live Sentinel workspace
- [ ] Verify authentication flow works with `DefaultAzureCredential`
- [ ] Confirm data is returned in expected format

**Deliverable:** Working Sentinel data access layer with tested KQL queries.

---

## Phase 3: Azure OpenAI Integration

### 3.1 OpenAI Client (`openai_client.py`)

- [ ] Implement `ChatClient` class wrapping `AzureOpenAI`
- [ ] Implement method: `chat(messages, tools)` — sends chat completion request with tool definitions
- [ ] Implement method: `embed(text)` — generates embeddings using text-embedding-3-large (1024 dimensions)
- [ ] Handle token counting with `tiktoken` to stay within context limits
- [ ] Implement conversation history management (keep last N exchanges, summarize older ones)

### 3.2 Tool Definitions (`tools.py`)

- [ ] Define tool schemas for all Sentinel query functions:
  - `query_sentinel_incidents` — filter by severity, status, time range
  - `get_incident_details` — look up specific incident by number
  - `query_sentinel_alerts` — filter alerts by severity and time
  - `run_kql_query` — execute predefined KQL templates
  - `search_knowledge_base` — search the vector store for historical context
  - `get_threat_summary` — get a high-level summary of current threat landscape

### 3.3 Tool Handler (`tool_handlers.py`)

- [ ] Implement dispatcher that maps tool call names to `SentinelClient` and `VectorStore` methods
- [ ] Parse tool call arguments from the LLM response
- [ ] Execute the corresponding function and return results
- [ ] Handle errors gracefully (return error descriptions that the LLM can interpret)

### 3.4 System Prompt (`prompts.py`)

- [ ] Write a system prompt that establishes the assistant's role as a security analyst assistant
- [ ] Include instructions for:
  - Using tools to fetch live Sentinel data before answering
  - Providing investigation recommendations based on MITRE ATT&CK framework
  - Summarizing threat information at appropriate detail levels
  - Citing incident numbers and timestamps in responses
  - Refusing non-security-related queries

**Deliverable:** Working Azure OpenAI integration with function calling and tool dispatch.

---

## Phase 4: Vector Store and Knowledge Base

### 4.1 ChromaDB Setup (`vector_store.py`)

- [ ] Implement `VectorStore` class with ChromaDB persistent client
- [ ] Implement method: `add_incidents(incidents)` — embed and store incident data with metadata
- [ ] Implement method: `search(query, n_results, severity_filter)` — semantic search with optional metadata filtering
- [ ] Implement method: `index_sentinel_data()` — bulk-load historical incidents from Sentinel into ChromaDB
- [ ] Use Azure OpenAI text-embedding-3-large for embedding generation

### 4.2 Data Ingestion Pipeline

- [ ] Implement a one-time ingestion script that:
  1. Queries Sentinel for historical incidents (last 30-90 days)
  2. Serializes each incident into natural-language text (title, severity, status, description, MITRE techniques, entities)
  3. Generates embeddings via Azure OpenAI
  4. Stores in ChromaDB with structured metadata (severity, status, timestamp, incident number)
- [ ] Add progress reporting for bulk ingestion
- [ ] Handle rate limiting from the embedding API (respect token-per-minute quotas)

### 4.3 Optional: Investigation Playbook Ingestion

- [ ] Create sample investigation playbooks as text files (e.g., "brute force investigation steps", "phishing response procedure")
- [ ] Index these into a separate ChromaDB collection for retrieval during conversations

**Deliverable:** Populated vector store with historical Sentinel data and optional playbooks.

---

## Phase 5: CLI Chat Interface

### 5.1 Chat Loop (`main.py`)

- [ ] Implement the main chat loop:
  1. Display welcome message with available capabilities
  2. Accept user input
  3. Send to Azure OpenAI with conversation history and tool definitions
  4. If LLM returns tool calls → execute tools → send results back to LLM → get final response
  5. Display response to user
  6. Repeat until user exits
- [ ] Use `rich` library for formatted terminal output (color-coded severity, tables for incident lists, markdown rendering)
- [ ] Support special commands:
  - `/quit` or `/exit` — end the session
  - `/clear` — reset conversation history
  - `/refresh` — re-index recent Sentinel data into vector store
  - `/status` — show connection status to Azure services

### 5.2 Multi-Turn Conversation

- [ ] Maintain conversation history across turns
- [ ] Implement token budget management — truncate or summarize older messages when approaching context limit
- [ ] Support follow-up questions that reference previous context ("tell me more about that incident")

### 5.3 Error Handling and User Experience

- [ ] Graceful handling of Azure API errors (auth failures, rate limits, timeouts)
- [ ] Loading indicators during API calls
- [ ] Clear error messages that suggest remediation steps

**Deliverable:** Fully functional CLI chatbot with formatted output and multi-turn conversation.

---

## Phase 6: Testing and Validation

### 6.1 Unit Tests

- [ ] Test `SentinelClient` methods with mocked API responses
- [ ] Test `ChatClient` tool calling flow with mocked OpenAI responses
- [ ] Test `VectorStore` operations with in-memory ChromaDB
- [ ] Test `config.py` validation logic
- [ ] Test tool handler dispatch logic

### 6.2 Integration Tests

- [ ] Test end-to-end flow: user query → tool calls → Sentinel API → LLM response (requires live Azure resources)
- [ ] Test vector store ingestion and retrieval accuracy
- [ ] Test conversation continuity across multiple turns

### 6.3 Validation Scenarios

Test the following user interactions to validate the POC meets requirements:

| Scenario | Example Query | Expected Behavior |
|----------|--------------|-------------------|
| **Active incidents** | "What are the current high-severity incidents?" | Queries Sentinel, returns list with details |
| **Incident details** | "Tell me more about incident 42" | Fetches specific incident with alerts and entities |
| **Threat summary** | "Summarize the threats from the last week" | Aggregates incidents/alerts, provides summary |
| **Investigation guidance** | "What should I investigate for this brute force alert?" | Retrieves playbook/historical context, provides MITRE-aligned steps |
| **Historical context** | "Have we seen this type of attack before?" | Searches vector store for similar past incidents |
| **Trend analysis** | "How has alert volume changed over the past 7 days?" | Runs KQL trend query, summarizes pattern |
| **Entity investigation** | "What entities have been most targeted this week?" | Queries top attacked entities, provides analysis |

### 6.4 Quality Assessment

- [ ] Evaluate response accuracy against known Sentinel data
- [ ] Evaluate response relevance and helpfulness for SOC workflows
- [ ] Identify and document any hallucination patterns
- [ ] Document latency for each interaction type

**Deliverable:** Test results documenting that each validation scenario works correctly.

---

## Phase 7: Demo Preparation and Local Deployment

### 7.1 Demo Environment

- [ ] Ensure the Sentinel workspace has sufficient and representative incident/alert data
  - If production data is sensitive, consider creating a dedicated demo workspace with realistic sample data
  - Alternative: use the Sentinel Training Lab sample data
- [ ] Pre-populate the ChromaDB vector store with historical data
- [ ] Test all validation scenarios on the demo environment

### 7.2 Demo Script

Prepare a scripted walkthrough covering:

1. **Introduction** — explain the architecture (reference the diagram in INITIAL-RESEARCH.md)
2. **Active threat overview** — "What are the current active incidents and their severity?"
3. **Deep dive** — "Tell me about the highest severity incident" → "What entities are involved?" → "What investigation steps do you recommend?"
4. **Historical context** — "Have we seen similar attacks in the past month?"
5. **Trend analysis** — "Give me a 7-day trend of security alerts by severity"
6. **SOC workflow value** — "Summarize today's security posture for a management briefing"

### 7.3 Documentation

- [ ] Write a `README.md` with:
  - Project overview and architecture diagram
  - Prerequisites and setup instructions
  - How to run the POC
  - Example interactions
  - Known limitations
  - Future roadmap (production considerations)

### 7.4 Local Deployment Checklist

- [ ] Verify all environment variables are set
- [ ] Verify Azure CLI authentication works
- [ ] Run the ingestion pipeline to populate the vector store
- [ ] Start the chatbot and run through all demo scenarios
- [ ] Confirm the demo runs without errors end-to-end

**Deliverable:** Demo-ready POC with documentation and scripted walkthrough.

---

## Timeline Overview

| Phase | Description | Dependencies |
|-------|-------------|-------------|
| **Phase 0** | Azure resource setup and configuration | Azure subscription access, admin permissions |
| **Phase 1** | Project scaffolding and core infrastructure | Phase 0 complete |
| **Phase 2** | Sentinel data access layer | Phase 1 complete |
| **Phase 3** | Azure OpenAI integration with function calling | Phase 1 complete (can parallel with Phase 2) |
| **Phase 4** | Vector store and knowledge base | Phase 2 + Phase 3 complete |
| **Phase 5** | CLI chat interface | Phase 2 + Phase 3 + Phase 4 complete |
| **Phase 6** | Testing and validation | Phase 5 complete |
| **Phase 7** | Demo preparation and local deployment | Phase 6 complete |

**Parallelization:** Phases 2 and 3 can be developed in parallel since they have no cross-dependencies until Phase 4 integrates them.

---

## Production Considerations (Post-POC)

These are explicitly **out of scope** for the POC but should be documented for leadership:

| Area | POC Approach | Production Approach |
|------|-------------|-------------------|
| **Vector store** | ChromaDB (local) | Azure AI Search with hybrid search and security trimming |
| **Authentication** | Service principal / Azure CLI | Managed Identity on Azure-hosted compute |
| **Deployment** | Local Python script | Azure Container Apps or Azure Functions |
| **RBAC** | Single service principal | Per-user access controls mapped to vector store ACLs |
| **Data freshness** | Manual ingestion script | Azure Functions timer trigger or Event Grid-based pipeline |
| **Monitoring** | Console logs | Application Insights + Azure Monitor |
| **Cost management** | Pay-as-you-go | Token budgets, caching, model selection per query type |
| **Multi-tenancy** | Single workspace | Multi-workspace with tenant isolation |
| **Prompt injection** | Basic system prompt guardrails | Multi-layered defenses (input validation, output filtering, auth service) |
| **Orchestration** | Direct OpenAI SDK | LangChain / Semantic Kernel / Azure AI Foundry Agent Service |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| gpt-4o not available in target Azure region | Medium | High | Check regional availability before starting; have fallback region |
| Sentinel workspace has insufficient test data | Medium | Medium | Use Sentinel Training Lab or create sample analytics rules |
| Azure OpenAI rate limits during bulk embedding | Low | Medium | Implement rate limiting with exponential backoff in ingestion |
| LLM hallucinations about incident data | Medium | High | Always ground responses in tool call results; include incident numbers |
| Service principal permission issues | Medium | Low | Test each permission independently during Phase 0 |
| Token context window exceeded | Low | Medium | Implement token counting and truncation with tiktoken |
