# Azure Sentinel + Azure OpenAI RAG Chatbot — Initial Research

> **Research Date:** February 2026
> **Purpose:** Evaluate feasibility and define technical approach for a POC command-line chatbot that allows SOC teams to query Microsoft Sentinel SIEM data using natural language via Azure OpenAI.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Microsoft Sentinel Data Access Methods](#2-microsoft-sentinel-data-access-methods)
3. [Azure OpenAI Models and SDK](#3-azure-openai-models-and-sdk)
4. [RAG Architecture Patterns for Security Data](#4-rag-architecture-patterns-for-security-data)
5. [Embedding Models and Vector Storage](#5-embedding-models-and-vector-storage)
6. [Function Calling for Dynamic Data Retrieval](#6-function-calling-for-dynamic-data-retrieval)
7. [Security Considerations](#7-security-considerations)
8. [Existing Integrations and Reference Projects](#8-existing-integrations-and-reference-projects)
9. [Dependencies and Prerequisites](#9-dependencies-and-prerequisites)
10. [Key Findings and Recommendations](#10-key-findings-and-recommendations)
11. [Sources](#11-sources)

---

## 1. Architecture Overview

The POC uses a **hybrid agentic RAG** architecture combining two retrieval strategies:

```
┌─────────────────────────────────────────────────────────┐
│                   CLI Chat Interface                     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Azure OpenAI (gpt-4o / gpt-4.1)            │
│         with function calling / tool definitions         │
└──────┬──────────────────────────────────┬───────────────┘
       │                                  │
       ▼                                  ▼
┌──────────────┐                ┌─────────────────────┐
│  Live Query  │                │  Vector Store Search │
│  (KQL via    │                │  (Historical data,   │
│  Log         │                │  playbooks, threat   │
│  Analytics)  │                │  intel — ChromaDB    │
└──────────────┘                │  for POC)            │
       │                        └─────────────────────┘
       ▼                                  │
┌──────────────┐                          │
│  Sentinel    │                          │
│  REST API    │                          │
│  (Incidents, │                          │
│   Alerts)    │                          │
└──────────────┘                          │
       │                                  │
       └──────────────┬──────────────────┘
                      ▼
         ┌────────────────────────┐
         │  LLM synthesizes      │
         │  response from both   │
         │  live + historical    │
         │  data sources         │
         └────────────────────────┘
```

**Why hybrid?** Active incidents and alerts change constantly — pre-indexed embeddings go stale quickly. The LLM uses **function calling** to query Sentinel's live APIs for current data, while a **vector store** provides context from historical incidents, investigation playbooks, and threat intelligence for enrichment and recommendations.

---

## 2. Microsoft Sentinel Data Access Methods

### 2.1 Sentinel REST API (ARM)

The primary management API for Sentinel resources. Current stable API version: **`2025-09-01`**.

**Base URL pattern:**
```
https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}/providers/Microsoft.SecurityInsights/...
```

**Key endpoints for the POC:**

| Operation | Method | Path |
|-----------|--------|------|
| List Incidents | `GET` | `.../incidents?api-version=2025-09-01` |
| Get Incident | `GET` | `.../incidents/{incidentId}?api-version=2025-09-01` |
| List Alerts for Incident | `POST` | `.../incidents/{incidentId}/alerts?api-version=2025-09-01` |
| List Entities for Incident | `POST` | `.../incidents/{incidentId}/entities?api-version=2025-09-01` |

**Filtering and pagination:**
- Supports `$filter`, `$orderby`, `$top`, `$skipToken` query parameters
- Pagination via `nextLink` URLs containing `$skipToken`
- Rate limits are per-operation, per-5-minutes, per-subscription; HTTP 429 returned with `Retry-After` header when exceeded

**Python access pattern (direct REST via azure-identity):**
```python
import requests
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
token = credential.get_token("https://management.azure.com/.default")

url = (
    f"https://management.azure.com/subscriptions/{sub_id}"
    f"/resourceGroups/{rg}/providers/Microsoft.OperationalInsights"
    f"/workspaces/{ws}/providers/Microsoft.SecurityInsights"
    f"/incidents?api-version=2025-09-01"
)
response = requests.get(url, headers={"Authorization": f"Bearer {token.token}"})
incidents = response.json()
```

> **Note:** The `azure-mgmt-securityinsight` Python package (v1.0.0, last released July 2022) is **stale and not recommended** for new projects. Use direct REST calls or KQL queries instead.

### 2.2 Azure Log Analytics / KQL Queries

Microsoft Sentinel stores all data in Log Analytics workspaces, queryable via KQL (Kusto Query Language). This is the **most flexible method** for accessing Sentinel data.

**Python SDK:** `azure-monitor-query` v2.0.0 (released July 2025)

```python
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from datetime import timedelta

credential = DefaultAzureCredential()
client = LogsQueryClient(credential)

response = client.query_workspace(
    workspace_id="<log-analytics-workspace-id>",
    query="""
    SecurityIncident
    | where TimeGenerated > ago(7d)
    | where Severity == "High"
    | project IncidentNumber, Title, Severity, Status, CreatedTime, ClosedTime
    | order by CreatedTime desc
    | take 50
    """,
    timespan=timedelta(days=7)
)
```

**Key Sentinel KQL tables:**

| Table | Description |
|-------|-------------|
| `SecurityIncident` | All Sentinel incidents with status, severity, owner, labels |
| `SecurityAlert` | Alerts from all security providers |
| `ThreatIntelIndicators` | STIX-based threat intelligence indicators (new, April 2025) |
| `ThreatIntelObjects` | STIX objects — threat actors, attack patterns, relationships |
| `CommonSecurityLog` | CEF/Syslog data from firewalls, proxies, etc. |
| `SigninLogs` | Entra ID sign-in events |
| `AuditLogs` | Entra ID audit events |

**Service limits:**
- Max 500,000 rows per query
- Max 64 MB data per query
- 8-minute timeout for standard queries
- Batch queries supported (multiple KQL queries in one call)

### 2.3 Microsoft Graph Security API

Provides unified access to security incidents and alerts across the Microsoft security stack.

**Key endpoints:**

| Operation | Endpoint |
|-----------|----------|
| List Incidents | `GET https://graph.microsoft.com/v1.0/security/incidents` |
| List Incidents + Alerts | `GET .../security/incidents?$expand=alerts` |
| List Alerts v2 | `GET https://graph.microsoft.com/v1.0/security/alerts_v2` |

**Python SDK:** `msgraph-sdk` v1.54.0

**Required permissions:** `SecurityIncident.Read.All`, `SecurityAlert.Read.All`

**When to use Graph vs. Sentinel REST API:**
- Graph API can return incidents with expanded alerts in a single call (`$expand=alerts`)
- Sentinel REST API requires separate calls for incidents and their alerts
- Graph API covers alerts from Defender products, Entra ID Protection, Purview, etc.
- For the POC, we primarily use KQL queries (most flexible) supplemented by Sentinel REST API for incident management operations

### 2.4 Sentinel MCP Server (GA November 2025)

Microsoft released a Model Context Protocol server for Sentinel providing 40+ read-only tools for LLMs. While promising for production, the POC will use direct API calls for simplicity and transparency.

---

## 3. Azure OpenAI Models and SDK

### 3.1 Recommended Models

| Model | Context Window | Best For | Notes |
|-------|---------------|----------|-------|
| **gpt-4o** | 128K tokens | General-purpose RAG, multimodal | Widely available, well-tested |
| **gpt-4.1** | 1M tokens | Long-context RAG, large result sets | Newer, strong instruction following |
| **gpt-4o-mini** | 128K tokens | Cost-efficient high-volume queries | Good for summarization tasks |
| **text-embedding-3-large** | 8,192 tokens | Embedding generation | Configurable dimensions |

**POC recommendation:** Use **gpt-4o** as the primary chat model (proven, widely available in Azure regions) with **text-embedding-3-large** for embeddings. The gpt-4o 128K context window is more than sufficient for a POC.

### 3.2 Python SDK

**Package:** `openai` v2.21.0 (February 2026)

**Azure OpenAI client setup:**
```python
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="https://<resource>.openai.azure.com/",
    api_key="<api-key>",
    api_version="2024-10-21"
)
```

**Token-based authentication (recommended):**
```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_endpoint="https://<resource>.openai.azure.com/",
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21"
)
```

### 3.3 Key API Notes

- The `functions` / `function_call` parameters are **deprecated**. Use `tools` / `tool_choice` instead.
- The Assistants API is being **sunset** in favor of the Responses API (full parity expected 2026).
- Azure now supports a **v1 API endpoint** (August 2025+) that removes the need for `api_version` parameter.
- The `openai` package moved from v1.x to v2.x in September 2025. New projects should use v2.x.

---

## 4. RAG Architecture Patterns for Security Data

### 4.1 Pattern A: Hybrid Structured + Semantic Retrieval

Store structured fields (severity, timestamp, IPs, MITRE techniques) as filterable metadata in the vector store. Embed free-text portions (alert descriptions, investigation notes) as vectors. Use hybrid queries combining keyword filters with vector similarity.

**Best for:** Historical incident search, "find similar past incidents" queries.

### 4.2 Pattern B: Agentic RAG with Function Calling (Recommended for POC)

The LLM decides which tools to call based on the user's query:

```
User: "What are the high-severity incidents from the last 24 hours?"
  → LLM calls: query_sentinel_incidents(severity="High", time_range_hours=24)
  → LLM synthesizes response from live API results

User: "What's the recommended investigation approach for this type of attack?"
  → LLM calls: search_knowledge_base(query="brute force investigation steps")
  → LLM provides recommendations from indexed playbooks/threat intel
```

**Best for:** Real-time queries about active incidents, dynamic data that changes frequently.

### 4.3 Pattern C: NL-to-KQL

The LLM generates KQL queries from natural language, executes them against Log Analytics, and summarizes results.

**Caveat:** LLMs produce buggy KQL for advanced scenarios. A validation layer is essential. For the POC, we use pre-defined KQL templates with parameter substitution rather than freeform generation.

### 4.4 Recommended POC Approach

**Combine Patterns B and A:**
1. **Function calling** for live Sentinel data (current incidents, active alerts, real-time status)
2. **Vector store retrieval** for historical context, investigation playbooks, and threat intelligence enrichment
3. **Pre-defined KQL templates** (not freeform generation) for common queries the LLM can invoke as tools

---

## 5. Embedding Models and Vector Storage

### 5.1 Embedding Model Selection

| Model | Dimensions | Max Tokens | Price/1M Tokens | Notes |
|-------|-----------|------------|-----------------|-------|
| **text-embedding-3-large** | Up to 3,072 (configurable) | 8,192 | $0.13 | Recommended |
| text-embedding-3-small | Up to 1,536 | 8,192 | $0.02 | Budget option |
| text-embedding-ada-002 | 1,536 (fixed) | 8,191 | $0.10 | Legacy — do not use |

**Recommendation:** Use **text-embedding-3-large at 1024 dimensions**. This gives near-full accuracy at 1/3 the storage cost — validated by benchmarks showing the 1024D truncation performs within 1-2% of the full 3072D on retrieval tasks.

### 5.2 Chunking Strategy for Security Data

**Individual alerts:** Treat each alert as a single chunk (alerts are typically well under 8K tokens). Serialize structured fields into natural-language format:

```
Alert: Suspicious Login Detected
Severity: High
Time: 2025-12-15T14:32:00Z
Source IP: 192.168.1.105
Destination: DC-01.contoso.com
MITRE Technique: T1078 - Valid Accounts
Description: Multiple failed login attempts followed by successful
authentication from an unusual geographic location.
```

Store structured fields (severity, timestamp, IPs, MITRE technique) as **filterable metadata** separately from the embedded text.

**Investigation playbooks / longer documents:** Use 400-token chunks with 10-20% overlap to preserve narrative coherence.

### 5.3 Vector Store Options

| Store | Best For | Metadata Filtering | Persistence | Setup |
|-------|----------|-------------------|-------------|-------|
| **ChromaDB** (v1.5.0) | POC / prototyping | Built-in | Built-in | Zero config |
| **FAISS** (v1.13.2) | Large-scale, GPU acceleration | Not included | Manual | Moderate |
| **Azure AI Search** (v11.6.0) | Production Azure RAG | Built-in + security trimming | Managed service | Azure resource required |

**POC recommendation:** Use **ChromaDB** for the fastest path to a working prototype. It provides built-in persistence, metadata filtering (filtering by severity, status, etc.), and requires zero infrastructure setup. Migrate to Azure AI Search when moving to production.

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection("sentinel_incidents")

collection.add(
    documents=["Incident summary text..."],
    metadatas=[{"severity": "High", "status": "Active"}],
    ids=["incident-001"]
)

results = collection.query(
    query_texts=["brute force attack"],
    n_results=5,
    where={"severity": "High"}
)
```

---

## 6. Function Calling for Dynamic Data Retrieval

### 6.1 Tool Definitions for Sentinel

The LLM uses function calling (`tools` parameter) to dynamically query Sentinel APIs. Example tool definitions:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_sentinel_incidents",
            "description": "Query Microsoft Sentinel for security incidents",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low", "Informational"],
                        "description": "Filter by incident severity"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["New", "Active", "Closed"],
                        "description": "Filter by incident status"
                    },
                    "time_range_hours": {
                        "type": "integer",
                        "description": "How many hours back to search"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["time_range_hours"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_incident_details",
            "description": "Get detailed information about a specific incident including alerts and entities",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_id": {
                        "type": "string",
                        "description": "The Sentinel incident ID"
                    }
                },
                "required": ["incident_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_kql_query",
            "description": "Run a predefined KQL query against Sentinel Log Analytics",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query_name": {
                        "type": "string",
                        "enum": [
                            "high_severity_alerts_24h",
                            "incident_timeline",
                            "top_attacked_entities",
                            "alert_trend_7d",
                            "failed_signins_by_ip"
                        ],
                        "description": "Name of the predefined KQL query template to run"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters to substitute into the query template",
                        "additionalProperties": True
                    }
                },
                "required": ["query_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search historical incidents and threat intelligence knowledge base",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "severity_filter": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low", "Informational"],
                        "description": "Optional severity filter"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    }
]
```

### 6.2 Parallel Function Calls

The model can invoke multiple tools simultaneously. For example, when a user asks "Give me a summary of today's security posture," the LLM might call:
1. `query_sentinel_incidents(time_range_hours=24)` — get today's incidents
2. `run_kql_query(query_name="alert_trend_7d")` — get alert trend context
3. `search_knowledge_base(query="security posture summary template")` — get reporting format

Each tool call has a unique `id`; the application responds with results keyed to each `tool_call_id`, and the LLM synthesizes a unified response.

---

## 7. Security Considerations

### 7.1 Data Sensitivity

- Sentinel data contains sensitive security information (IPs, usernames, attack details, infrastructure topology)
- All data must remain within the organization's Azure tenant boundary
- For the POC, use environment variables or Azure Key Vault for credentials — never hardcode secrets
- The vector store (ChromaDB) stores data locally — ensure the POC machine has appropriate access controls

### 7.2 Authentication and RBAC

**Required Azure AD roles for the POC service principal:**

| Role | Scope | Purpose |
|------|-------|---------|
| Microsoft Sentinel Reader | Sentinel workspace | Read incidents, alerts, analytics rules |
| Log Analytics Reader | Log Analytics workspace | Run KQL queries |
| Cognitive Services OpenAI User | Azure OpenAI resource | Call chat and embedding models |

**Authentication chain (recommended):**
- Local development: `AzureCliCredential` (via `DefaultAzureCredential`)
- Service principal: `ClientSecretCredential` with environment variables
- Use `DefaultAzureCredential` to support both scenarios transparently

### 7.3 Prompt Injection Prevention

For the POC, implement basic guardrails:
- System prompt instructs the model to only answer security-related questions
- Retrieved Sentinel data is placed in clearly labeled context blocks (not inline with instructions)
- Pre-defined KQL query templates prevent arbitrary query injection
- No write operations exposed to the LLM — all tools are read-only

### 7.4 OWASP Considerations

OWASP added "Vector and Embedding Weaknesses" as a Top 10 LLM risk in 2025. For production:
- Encrypt vector stores at rest (AES-256)
- Implement per-user access controls on retrieved documents
- Apply sensitive data filtering before embedding (mask PII, secrets)
- Audit all queries and responses

---

## 8. Existing Integrations and Reference Projects

### 8.1 GitHub Repositories

| Repository | Description |
|---|---|
| [format81/MicrosoftSentinel-AzureOpenAI-IR-helper-playbook](https://github.com/format81/MicrosoftSentinel-AzureOpenAI-IR-helper-playbook) | Logic App playbook using Azure OpenAI to explain MITRE tactics, suggest investigation steps, generate KQL |
| [dstreefkerk/ms-sentinel-mcp-server](https://github.com/dstreefkerk/ms-sentinel-mcp-server) | MCP server providing 40+ read-only Sentinel tools for LLMs |
| [briandelmsft/SentinelAutomationModules](https://github.com/briandelmsft/SentinelAutomationModules) | STAT (Sentinel Triage AssistanT) — automated incident triage |
| [Azure-Samples/azure-search-classic-rag](https://github.com/Azure-Samples/azure-search-classic-rag) | Microsoft's official classic RAG pattern sample |

### 8.2 Key Blog Posts and Articles

- [Introduction to OpenAI and Microsoft Sentinel (Microsoft Tech Community)](https://techcommunity.microsoft.com/blog/manufacturing/introduction-to-openai-and-microsoft-sentinel/3761907) — four-part series on Sentinel + OpenAI integration via Logic Apps
- [Microsoft Sentinel and Azure OpenAI (Thoor.tech)](https://thoor.tech/sentinel-and-azure-openai/) — building a security chatbot with Sentinel and KQL
- [CyberRAG: Agentic Classification + RAG (arXiv)](https://arxiv.org/html/2507.02424v1) — framework reducing analyst triage time by ~45% in pilot deployment

### 8.3 Microsoft Security Copilot Context

Security Copilot (included in M365 E5 as of Ignite 2025) is the "buy" option. Our custom RAG solution is the "build" option, offering:
- Full control over models, prompts, and retrieval logic
- Ability to integrate non-Microsoft data sources
- Lower ongoing cost (pay-as-you-go Azure OpenAI vs. SCU consumption)
- Complete data flow transparency for audit and compliance

---

## 9. Dependencies and Prerequisites

### 9.1 Azure Resources Required

| Resource | SKU / Tier | Purpose |
|----------|-----------|---------|
| **Azure OpenAI Service** | Standard S0 | Chat completions (gpt-4o) and embeddings (text-embedding-3-large) |
| **Microsoft Sentinel** | Pay-as-you-go | SIEM data source (must have active workspace with incidents/alerts) |
| **Log Analytics Workspace** | Per-GB | Underlying data store for Sentinel (created with Sentinel) |
| **Azure AD App Registration** | Free | Service principal for API authentication |
| **Azure Key Vault** (optional) | Standard | Secret management for credentials |

### 9.2 Azure OpenAI Model Deployments

The following models must be deployed in the Azure OpenAI resource:

| Deployment Name | Model | Purpose |
|----------------|-------|---------|
| `gpt-4o` | gpt-4o (2024-11-20 or later) | Chat completions, function calling |
| `text-embedding-3-large` | text-embedding-3-large | Generating embeddings for vector store |

### 9.3 Python Environment

**Minimum Python version:** 3.10+ (required by LangChain)

### 9.4 Python Dependencies

```
# Core Azure SDKs
azure-identity>=1.25.0
azure-monitor-query>=2.0.0
azure-search-documents>=11.6.0

# Azure OpenAI
openai>=2.20.0

# Orchestration (optional — POC can work without it)
langchain>=1.2.0
langchain-openai>=1.1.0
langchain-community>=0.4.0
langchain-chroma>=0.2.0

# Local vector store for POC
chromadb>=1.5.0

# Utilities
tiktoken>=0.12.0
python-dotenv>=1.0.0
requests>=2.31.0
rich>=13.0.0          # CLI output formatting
```

**Install command:**
```bash
pip install azure-identity azure-monitor-query openai chromadb tiktoken python-dotenv requests rich
```

### 9.5 Azure AD Permissions

**For Sentinel REST API and KQL queries:**
- App role: Microsoft Sentinel Reader on the Sentinel workspace
- App role: Log Analytics Reader on the Log Analytics workspace

**For Azure OpenAI:**
- App role: Cognitive Services OpenAI User on the Azure OpenAI resource

**For Microsoft Graph Security API (if used):**
- Application permission: `SecurityIncident.Read.All`
- Application permission: `SecurityAlert.Read.All`

### 9.6 Environment Variables

The POC expects the following environment variables (or `.env` file):

```bash
# Azure AD / Service Principal
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>          # or use token-based auth
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-10-21

# Sentinel / Log Analytics
SENTINEL_WORKSPACE_ID=<log-analytics-workspace-guid>
SENTINEL_SUBSCRIPTION_ID=<azure-subscription-id>
SENTINEL_RESOURCE_GROUP=<resource-group-name>
SENTINEL_WORKSPACE_NAME=<workspace-name>
```

### 9.7 Local Development Tools

- Python 3.10+
- Azure CLI (`az`) — for `DefaultAzureCredential` authentication during development
- Git
- A terminal with UTF-8 support (for rich CLI formatting)

---

## 10. Key Findings and Recommendations

### 10.1 Feasibility Assessment: CONFIRMED

The integration is technically feasible and well-supported by current Azure tooling. Multiple reference implementations and Microsoft's own documentation validate the approach.

### 10.2 Primary Data Access Method

Use **KQL queries via `azure-monitor-query`** as the primary data access method. This is the most flexible approach, supports all Sentinel tables, and avoids the stale `azure-mgmt-securityinsight` package. Supplement with direct REST calls to the Sentinel API for incident management operations (listing incidents with pagination, getting incident details).

### 10.3 Architecture Decision

Use **agentic RAG with function calling** rather than pre-indexing all Sentinel data:
- Active incident data changes constantly — embeddings would go stale
- Function calling lets the LLM decide what data to fetch based on the question
- ChromaDB provides a local vector store for historical context and playbooks
- This approach is simpler to build and demonstrates the concept effectively

### 10.4 Model Selection

- **gpt-4o** for chat (proven, widely available, 128K context sufficient for POC)
- **text-embedding-3-large at 1024 dimensions** for embeddings (best quality/cost ratio)

### 10.5 Orchestration Framework

For the POC, **build without LangChain** — use the OpenAI SDK directly with function calling. This keeps the POC simple, transparent, and easy to understand for leadership demos. LangChain can be introduced later if the project moves to production.

### 10.6 Critical Risks

1. **Azure OpenAI regional availability:** gpt-4o may not be available in all Azure regions. Verify deployment availability before starting.
2. **Sentinel data volume:** Large enterprises may have thousands of incidents. Implement pagination and time-range filtering in all queries.
3. **KQL generation quality:** LLMs produce buggy KQL for advanced queries. Use pre-defined templates, not freeform generation.
4. **Token budget management:** Sentinel incident data can be verbose. Use tiktoken to count tokens and truncate context as needed before sending to the LLM.

---

## 11. Sources

### Microsoft Documentation
- [Microsoft Sentinel REST API Reference](https://learn.microsoft.com/en-us/rest/api/securityinsights/)
- [Sentinel API Versions — 2025-09-01](https://learn.microsoft.com/en-us/rest/api/securityinsights/api-versions)
- [Azure Monitor Query Client Library for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme)
- [Microsoft Graph Security API Overview](https://learn.microsoft.com/en-us/graph/api/resources/security-api-overview)
- [Azure OpenAI Function Calling](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/function-calling)
- [Azure OpenAI Responses API](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/responses)
- [Azure AI Search — RAG Overview](https://learn.microsoft.com/en-us/azure/search/retrieval-augmented-generation-overview)
- [Azure Identity Client Library](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
- [What's New in Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/whats-new)
- [Microsoft Sentinel MCP Server — GA Announcement](https://techcommunity.microsoft.com/blog/microsoft-security-blog/microsoft-sentinel-mcp-server---generally-available-with-exciting-new-capabiliti/4470125)

### Research Papers and Technical Articles
- [CyberRAG: Agentic Classification + RAG (arXiv 2507.02424)](https://arxiv.org/html/2507.02424v1)
- [Securing AI Agents Against Prompt Injection (arXiv 2511.15759)](https://arxiv.org/abs/2511.15759)
- [AgCyRAG: Knowledge Graph-Enhanced Security RAG (CEUR-WS)](https://ceur-ws.org/Vol-4079/paper11.pdf)
- [Hyper-Automation SOAR with Agentic AI (MDPI)](https://www.mdpi.com/2078-2489/16/5/365)

### Community Resources
- [Microsoft Sentinel and Azure OpenAI (Thoor.tech)](https://thoor.tech/sentinel-and-azure-openai/)
- [Sentinel REST APIs vs MS Graph (Gary Bushey)](https://garybushey.com/2025/01/13/microsoft-sentinel-rest-apis-vs-ms-graph/)
- [ms-sentinel-mcp-server (GitHub)](https://github.com/dstreefkerk/ms-sentinel-mcp-server)
- [MicrosoftSentinel-AzureOpenAI-IR-helper-playbook (GitHub)](https://github.com/format81/MicrosoftSentinel-AzureOpenAI-IR-helper-playbook)
- [Microsoft Sentinel as Agentic Platform (Microsoft Security Blog)](https://www.microsoft.com/en-us/security/blog/2025/09/30/empowering-defenders-in-the-era-of-agentic-ai-with-microsoft-sentinel/)

### Package Registries
- [openai v2.21.0 (PyPI)](https://pypi.org/project/openai/)
- [azure-monitor-query v2.0.0 (PyPI)](https://pypi.org/project/azure-monitor-query/)
- [azure-identity (PyPI)](https://pypi.org/project/azure-identity/)
- [chromadb v1.5.0 (PyPI)](https://pypi.org/project/chromadb/)
- [msgraph-sdk v1.54.0 (PyPI)](https://pypi.org/project/msgraph-sdk/)
- [tiktoken v0.12.0 (PyPI)](https://pypi.org/project/tiktoken/)
