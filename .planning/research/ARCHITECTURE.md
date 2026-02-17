# Architecture Research

**Domain:** Agentic RAG Security Chatbot (Python CLI / Azure OpenAI / Microsoft Sentinel)
**Researched:** 2026-02-16
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
+===================================================================+
|                       PRESENTATION LAYER                          |
|                                                                   |
|  +-------------------------------------------------------------+ |
|  |  main.py  --  CLI Chat Loop (rich-formatted terminal I/O)   | |
|  |  - User input capture                                       | |
|  |  - Response rendering (tables, markdown, color-coded)       | |
|  |  - Slash-command dispatch (/quit, /clear, /status, /refresh)| |
|  +------------------------------+------------------------------+ |
|                                  |                                |
+==================================|================================+
                                   |
+==================================|================================+
|                       ORCHESTRATION LAYER                         |
|                                                                   |
|  +------------------------------v------------------------------+ |
|  |  openai_client.py  --  Conversation Manager                 | |
|  |  - Manages message history (system + user + assistant + tool)| |
|  |  - Sends chat completion requests with tool definitions     | |
|  |  - Implements the TOOL LOOP: detect tool_calls -> dispatch  | |
|  |    -> collect results -> re-send to model -> repeat/return  | |
|  |  - Token budget management via tiktoken                     | |
|  +------+-------------------+-------------------+--------------+ |
|         |                   |                   |                 |
|  +------v------+   +--------v--------+   +------v-----------+   |
|  | prompts.py  |   |   tools.py      |   | tool_handlers.py |   |
|  | System      |   |   Tool schema   |   | Dispatcher: maps |   |
|  | prompt +    |   |   definitions   |   | tool name ->     |   |
|  | templates   |   |   (JSON spec)   |   | handler function |   |
|  +-------------+   +-----------------+   +------+-----------+   |
|                                                  |                |
+==================================================|================+
                                                   |
          +--------------------+-------------------+
          |                                        |
+==========|========+                  +=============|==============+
| LIVE DATA LAYER  |                  |  KNOWLEDGE LAYER           |
|                  |                  |                             |
| +----------------v---------+       | +---------------------------v+ |
| | sentinel_client.py       |       | | vector_store.py            | |
| | - LogsQueryClient (KQL)  |       | | - ChromaDB PersistentClient| |
| | - REST API calls         |       | | - Embedding via OpenAI     | |
| | - Predefined KQL         |       | | - Metadata filtering       | |
| |   templates with         |       | | - Semantic search          | |
| |   parameter substitution |       | +----------------------------+ |
| +-----------+---------+----+       |              |               |
|             |         |            |              |               |
| +-----------v--+ +----v--------+  | +-------------v------------+ |
| | Log Analytics| | Sentinel    |  | | ChromaDB                 | |
| | Workspace    | | REST API    |  | | (local persistent store) | |
| | (KQL tables) | | (incidents, |  | | - sentinel_incidents     | |
| |              | |  alerts,    |  | |   collection             | |
| |              | |  entities)  |  | | - playbooks collection   | |
| +--------------+ +-------------+  | +--------------------------+ |
|                                   |                              |
+===================================+==============================+
                                    |
+==============================================+
|               FOUNDATION LAYER               |
|                                              |
|  +------------------+  +------------------+  |
|  | config.py        |  | azure-identity   |  |
|  | - .env loading   |  | - DefaultAzure   |  |
|  | - Validation     |  |   Credential     |  |
|  | - Settings obj   |  | - Token caching  |  |
|  +------------------+  +------------------+  |
+===============================================+
```

### Component Responsibilities

| Component | Responsibility | Owns |
|-----------|----------------|------|
| `main.py` | CLI entry point, user I/O, slash commands, display formatting | The input/output boundary; no business logic |
| `openai_client.py` | Conversation orchestration, tool loop execution, token management | Message history, LLM API calls, the tool-call-resolve-repeat loop |
| `tools.py` | Tool schema definitions (JSON) for OpenAI function calling | The contract between the LLM and the application |
| `tool_handlers.py` | Dispatch layer mapping tool call names to concrete handler functions | The routing table; translates LLM intent into function calls |
| `prompts.py` | System prompt, prompt templates, output format instructions | The LLM's behavioral instructions |
| `sentinel_client.py` | Live data access: KQL queries and Sentinel REST API calls | KQL templates, API pagination, response formatting |
| `vector_store.py` | Historical data and playbook retrieval via ChromaDB | Embedding generation, collection management, semantic search |
| `config.py` | Environment configuration, validation, secrets management | All settings; single source of truth for config |

## Recommended Project Structure

```
azureAI-sentinel/
+-- src/
|   +-- __init__.py
|   +-- main.py               # CLI entry point: chat loop, rich rendering, slash commands
|   +-- config.py             # Settings class, .env loading, validation
|   +-- openai_client.py      # ChatClient class: completions, embeddings, tool loop
|   +-- sentinel_client.py    # SentinelClient class: KQL queries, REST API calls
|   +-- tools.py              # TOOL_DEFINITIONS list (JSON schema for OpenAI)
|   +-- tool_handlers.py      # ToolHandler class: dispatch table, error wrapping
|   +-- vector_store.py       # VectorStore class: ChromaDB operations, embedding
|   +-- prompts.py            # SYSTEM_PROMPT, KQL_TEMPLATES dict, format templates
+-- tests/
|   +-- __init__.py
|   +-- conftest.py           # Shared fixtures (mock clients, sample data)
|   +-- test_config.py
|   +-- test_sentinel_client.py
|   +-- test_openai_client.py
|   +-- test_tool_handlers.py
|   +-- test_vector_store.py
+-- data/
|   +-- chroma_db/            # ChromaDB persistent storage (gitignored)
|   +-- playbooks/            # Sample investigation playbook text files
+-- .env.example              # Template with variable names, no secrets
+-- .gitignore
+-- requirements.txt
+-- README.md
```

### Structure Rationale

- **Flat `src/` module:** Eight files with clear single responsibilities. No subdirectories needed at POC scale -- each file maps to exactly one architectural component. This keeps import paths simple (`from src.config import Settings`) and avoids over-engineering.
- **Separate `tools.py` from `tool_handlers.py`:** The schema definitions (what the LLM sees) are pure data -- no imports needed. The handlers (what executes) depend on sentinel_client and vector_store. Separating them means tools.py can be modified without touching execution logic, and vice versa.
- **`data/playbooks/`:** Plain text playbook files that get ingested into ChromaDB. Easier to author and review than embedded strings.
- **`tests/` mirrors `src/`:** One test file per source module for clear test coverage mapping.

## Architectural Patterns

### Pattern 1: The Tool Loop (Core Orchestration Pattern)

**What:** The central control flow of an agentic RAG system. The application sends a user message to the LLM with tool definitions; if the LLM responds with `tool_calls`, the application executes each tool, appends results as `tool` messages, and re-sends to the LLM. This loop repeats until the LLM returns a content-only response (no tool calls).

**When to use:** Every turn of conversation. This is the heartbeat of the application.

**Trade-offs:**
- PRO: The LLM decides what data to fetch -- no rigid query routing logic needed
- PRO: Supports parallel tool calls (LLM can request multiple tools in a single response)
- CON: Each loop iteration is another API call (latency + cost)
- CON: Must guard against infinite loops (set a max iteration count)

**Example (verified against official Microsoft docs, updated 2026-02-10):**

```python
import json
from openai import AzureOpenAI

MAX_TOOL_ROUNDS = 5  # Safety limit to prevent runaway loops

def run_tool_loop(
    client: AzureOpenAI,
    messages: list[dict],
    tools: list[dict],
    tool_dispatch: dict[str, callable],
    deployment: str,
) -> str:
    """Execute the tool loop until the LLM returns a final text response."""

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages.append(assistant_message)  # Append full message object

        # If no tool calls, we have our final response
        if not assistant_message.tool_calls:
            return assistant_message.content

        # Execute each tool call and append results
        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            # Dispatch to the appropriate handler
            handler = tool_dispatch.get(func_name)
            if handler:
                try:
                    result = handler(**func_args)
                except Exception as e:
                    result = json.dumps({"error": str(e)})
            else:
                result = json.dumps({"error": f"Unknown tool: {func_name}"})

            # Append tool result keyed to the specific tool_call_id
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": result if isinstance(result, str) else json.dumps(result),
            })

    # Safety: if we exhausted rounds, ask model to respond without tools
    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        tool_choice="none",  # Force a text response
    )
    return response.choices[0].message.content
```

**Critical details from official docs (HIGH confidence):**
1. Each `tool_call` has a unique `id`. The tool result message **must** reference it via `tool_call_id`.
2. The assistant message containing `tool_calls` must be appended to `messages` **as-is** (the full message object) before appending tool results.
3. The model can return multiple `tool_calls` in a single response (parallel function calling). All results must be appended before the next API call.
4. `tool_choice="auto"` is the default -- model decides whether to call tools.
5. `tool_choice="none"` forces a text-only response (useful for the safety fallback).

### Pattern 2: Dispatch Table for Tool Handlers

**What:** A dictionary mapping tool names (strings matching the `name` field in tool definitions) to handler functions. Keeps routing clean, extensible, and testable.

**When to use:** Always. Even with a small number of tools. Avoids if/elif chains that grow unmanageably.

**Trade-offs:**
- PRO: Adding a new tool is two steps: add schema to `tools.py`, add handler to dispatch table
- PRO: Each handler is independently testable
- CON: Slight indirection (tool name is a string key, not a direct function reference)

**Example:**

```python
# tool_handlers.py
import json
from src.sentinel_client import SentinelClient
from src.vector_store import VectorStore

class ToolHandler:
    def __init__(self, sentinel: SentinelClient, vector_store: VectorStore):
        self.sentinel = sentinel
        self.vector_store = vector_store

        # The dispatch table: tool name -> handler method
        self._dispatch = {
            "query_sentinel_incidents": self._handle_query_incidents,
            "get_incident_details": self._handle_get_incident,
            "query_sentinel_alerts": self._handle_query_alerts,
            "run_kql_query": self._handle_kql_query,
            "search_knowledge_base": self._handle_search_kb,
            "get_threat_summary": self._handle_threat_summary,
        }

    def get_dispatch_table(self) -> dict[str, callable]:
        """Return the dispatch table for use in the tool loop."""
        return self._dispatch

    def _handle_query_incidents(self, **kwargs) -> str:
        results = self.sentinel.query_incidents(**kwargs)
        return json.dumps(results, default=str)

    def _handle_search_kb(self, **kwargs) -> str:
        results = self.vector_store.search(**kwargs)
        return json.dumps(results, default=str)

    # ... other handlers follow same pattern
```

### Pattern 3: KQL Template Registry (Parameterized Queries)

**What:** A dictionary of named KQL query templates with parameter placeholders. The LLM selects a template by name and provides parameters; the application performs safe substitution. No freeform KQL generation.

**When to use:** For all KQL queries in this project. The INITIAL-RESEARCH.md correctly identifies that LLMs produce buggy KQL for advanced scenarios.

**Trade-offs:**
- PRO: Prevents KQL injection and malformed queries
- PRO: Each template is tested and known to work
- CON: Limited to pre-defined query patterns (cannot answer arbitrary KQL questions)
- CON: Adding new query types requires code changes

**Example:**

```python
# prompts.py (or a dedicated kql_templates.py)
KQL_TEMPLATES = {
    "high_severity_alerts_24h": """
        SecurityAlert
        | where TimeGenerated > ago({time_range}h)
        | where AlertSeverity == "High"
        | project AlertName, AlertSeverity, TimeGenerated, Entities
        | order by TimeGenerated desc
        | take {max_results}
    """,
    "incident_timeline": """
        SecurityIncident
        | where TimeGenerated > ago({days}d)
        | summarize count() by bin(CreatedTime, 1h), Severity
        | order by CreatedTime asc
    """,
    "failed_signins_by_ip": """
        SigninLogs
        | where TimeGenerated > ago({time_range}h)
        | where ResultType != 0
        | summarize FailedAttempts=count() by IPAddress, UserPrincipalName
        | order by FailedAttempts desc
        | take {max_results}
    """,
}

def render_kql(template_name: str, params: dict) -> str:
    """Safely render a KQL template with parameters."""
    template = KQL_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Unknown KQL template: {template_name}")
    # Use str.format with only known keys -- no arbitrary injection
    return template.format(**params)
```

### Pattern 4: Conversation History Management with Token Budgeting

**What:** Maintain a sliding window of conversation messages, using tiktoken to count tokens and truncate older messages when approaching the model's context limit. Reserve token budgets for system prompt, tool definitions, tool results, and the model's response.

**When to use:** Every multi-turn conversation. The 128K context window sounds large, but Sentinel data can be verbose (incident details, alert entities, KQL result sets).

**Trade-offs:**
- PRO: Prevents context overflow errors
- PRO: Keeps conversations responsive (shorter context = faster inference)
- CON: Older context is lost (user may reference something that was truncated)
- CON: Token counting adds slight overhead per turn

**Example:**

```python
# Token budget allocation for gpt-4o (128K context)
TOKEN_BUDGET = {
    "total": 128_000,
    "system_prompt": 2_000,      # Reserved for system instructions
    "tool_definitions": 3_000,   # Reserved for tool JSON schemas
    "tool_results": 40_000,      # Reserved for tool call results (Sentinel data)
    "response": 4_096,           # Reserved for model's response
    # Remaining ~79K available for conversation history
}

HISTORY_BUDGET = (
    TOKEN_BUDGET["total"]
    - TOKEN_BUDGET["system_prompt"]
    - TOKEN_BUDGET["tool_definitions"]
    - TOKEN_BUDGET["tool_results"]
    - TOKEN_BUDGET["response"]
)

def trim_history(messages: list[dict], max_tokens: int = HISTORY_BUDGET) -> list[dict]:
    """Keep the system message and most recent messages within token budget."""
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-4o")

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    # Count tokens from most recent backward
    kept = []
    total = sum(len(enc.encode(str(m.get("content", "")))) for m in system_messages)

    for msg in reversed(non_system):
        msg_tokens = len(enc.encode(str(msg.get("content", ""))))
        if total + msg_tokens > max_tokens:
            break
        kept.insert(0, msg)
        total += msg_tokens

    return system_messages + kept
```

### Pattern 5: Error Wrapping for Tool Results

**What:** Every tool handler wraps its execution in try/except and returns a JSON string describing the error. The LLM can then explain the error to the user in natural language rather than the application crashing.

**When to use:** Every tool handler, without exception. Azure API calls can fail for many reasons (auth expired, rate limited, workspace not found, KQL syntax error).

**Trade-offs:**
- PRO: The LLM gracefully explains failures ("I wasn't able to query Sentinel because...")
- PRO: The application never crashes from a tool execution failure
- CON: Errors may be imprecise if too aggressively caught

**Example:**

```python
def safe_tool_call(func, **kwargs) -> str:
    """Execute a tool handler with error wrapping."""
    try:
        result = func(**kwargs)
        return result if isinstance(result, str) else json.dumps(result, default=str)
    except HttpResponseError as e:
        return json.dumps({
            "error": "Azure API error",
            "code": e.error.code if e.error else "unknown",
            "message": str(e.message),
        })
    except Exception as e:
        return json.dumps({
            "error": "Tool execution failed",
            "type": type(e).__name__,
            "message": str(e),
        })
```

## Data Flow

### Primary Request Flow (Single Turn)

```
User types query
    |
    v
main.py: capture input, append {"role": "user", "content": query} to messages
    |
    v
openai_client.py: trim_history(messages) to fit token budget
    |
    v
openai_client.py: client.chat.completions.create(
    model=deployment, messages=messages, tools=TOOL_DEFINITIONS, tool_choice="auto"
)
    |
    +-- LLM returns content (no tool_calls) --> render response, done
    |
    +-- LLM returns tool_calls -->
        |
        v
    tool_handlers.py: for each tool_call:
        |
        +-- "query_sentinel_incidents" --> sentinel_client.query_incidents()
        |       |
        |       v
        |   LogsQueryClient.query_workspace() --> KQL against Log Analytics
        |       |
        |       v
        |   Format rows as JSON string --> append as tool message
        |
        +-- "search_knowledge_base" --> vector_store.search()
        |       |
        |       v
        |   ChromaDB collection.query() --> semantic search results
        |       |
        |       v
        |   Format results as JSON string --> append as tool message
        |
        +-- (other tools follow same dispatch pattern)
        |
        v
    openai_client.py: re-send messages (now including tool results) to LLM
        |
        +-- LLM may request MORE tools (loop continues, up to MAX_TOOL_ROUNDS)
        +-- LLM returns final content --> render response, done
```

### Data Ingestion Flow (One-Time / Periodic)

```
Ingestion script (or /refresh command)
    |
    v
sentinel_client.py: query_incidents(time_range_hours=2160)  # 90 days
    |
    v
For each incident:
    |
    +-- Serialize to natural language text (title, severity, description, MITRE, entities)
    |
    +-- openai_client.py: embed(text) --> Azure OpenAI text-embedding-3-large (1024 dims)
    |
    +-- vector_store.py: collection.add(
    |       documents=[text],
    |       metadatas=[{"severity": "High", "incident_number": 42, ...}],
    |       ids=["incident-42"]
    |   )
    |
    v
ChromaDB persistent storage updated on disk (data/chroma_db/)
```

### Conversation State Management

```
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},      # Always first, never removed
    {"role": "user", "content": "..."},                  # Turn 1 user
    {"role": "assistant", "content": "...", tool_calls: [...]},  # Turn 1 assistant (with tools)
    {"role": "tool", "tool_call_id": "...", "content": "..."}, # Turn 1 tool results
    {"role": "assistant", "content": "Here are the ..."},       # Turn 1 final response
    {"role": "user", "content": "..."},                  # Turn 2 user
    ...
]

# On each new turn:
# 1. Append new user message
# 2. Trim history from the MIDDLE (keep system + recent turns)
# 3. Enter tool loop
# 4. Append all assistant/tool messages from tool loop
# 5. Return final assistant content for display
```

### Key Data Flows

1. **Live query flow:** User question -> LLM selects tool -> sentinel_client executes KQL or REST call -> results formatted as JSON string -> LLM synthesizes natural language answer
2. **Knowledge retrieval flow:** User question -> LLM selects search_knowledge_base -> vector_store performs semantic search in ChromaDB -> matching documents with metadata -> LLM uses historical context to enrich response
3. **Hybrid flow:** User asks complex question -> LLM calls BOTH live query AND knowledge base tools in parallel -> both results returned -> LLM synthesizes a response grounding live data with historical context

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| POC (1-5 users, local) | Current architecture: single-process CLI, local ChromaDB, direct Azure API calls. No changes needed. |
| Team tool (5-50 users) | Add a lightweight web API (FastAPI) in front of the orchestration layer. Replace CLI with web UI or Teams bot. ChromaDB still sufficient. Add structured logging. |
| Department (50-500 users) | Replace ChromaDB with Azure AI Search (hybrid search, security trimming, managed service). Add per-user auth. Deploy on Azure Container Apps. Add Application Insights. Token-level caching for repeated queries. |
| Enterprise (500+ users) | Multi-workspace support. Per-user RBAC on vector store results. Rate limiting and queue-based request handling. Consider Azure AI Foundry Agent Service for managed orchestration. Cost management via model tiering (gpt-4o-mini for simple queries). |

### Scaling Priorities

1. **First bottleneck: Azure OpenAI rate limits.** The embedding API and chat completions API both have tokens-per-minute (TPM) quotas. At team scale, implement request queuing and exponential backoff. At department scale, provision higher TPM quotas or use multiple deployments.
2. **Second bottleneck: ChromaDB single-process limitation.** ChromaDB is not designed for concurrent multi-user access. At team scale, this becomes a problem. Migrate to Azure AI Search which handles concurrent reads natively.
3. **Third bottleneck: Sentinel API rate limits.** The Sentinel REST API and Log Analytics KQL API both throttle per-subscription. At scale, implement response caching (cache recent incident lists for 60 seconds) and batch KQL queries where possible.

## Anti-Patterns

### Anti-Pattern 1: Freeform KQL Generation

**What people do:** Let the LLM generate arbitrary KQL queries from natural language, execute them directly against Log Analytics.

**Why it's wrong:** LLMs produce syntactically incorrect KQL for anything beyond simple queries. Advanced KQL operators (`mv-expand`, `parse`, `evaluate`, nested `let` statements) are routinely malformed. Failed queries waste API calls and produce confusing error messages for users. Worse, malformed KQL could accidentally return unexpected data volumes (missing `take` or `where` clauses).

**Do this instead:** Use the KQL Template Registry pattern (Pattern 3). Pre-define tested query templates. The LLM selects a template name and provides parameters. Add new templates as needed based on user feedback.

### Anti-Pattern 2: Unbounded Conversation History

**What people do:** Append every message to the conversation history without ever trimming, relying on the 128K context window being "big enough."

**Why it's wrong:** Sentinel tool results can be large -- a single query_sentinel_incidents call with 50 incidents can return 10K+ tokens. After a few multi-tool turns, the context fills up. When it overflows, you get a hard error from the API. Even before overflow, longer contexts increase latency and cost linearly.

**Do this instead:** Implement token budgeting (Pattern 4). Count tokens per turn. Trim from the middle of history, preserving the system prompt and the most recent turns.

### Anti-Pattern 3: Direct Azure Client Construction in Handlers

**What people do:** Create `LogsQueryClient`, `AzureOpenAI`, and `ChromaDB` client instances inside individual handler functions.

**Why it's wrong:** These clients perform authentication on construction (token exchange, credential validation). Creating them per-call wastes time and may trigger rate limits. It also makes testing impossible without mocking at the import level.

**Do this instead:** Create all clients once in `main.py` during startup. Inject them into `SentinelClient`, `ChatClient`, and `VectorStore` classes as constructor parameters. This enables dependency injection for testing and amortizes authentication cost.

### Anti-Pattern 4: Embedding Tool Results in System Prompt

**What people do:** Pre-fetch Sentinel data and stuff it into the system prompt to "give the LLM context."

**Why it's wrong:** Pre-fetched data goes stale within minutes for active security incidents. It consumes a fixed chunk of the token budget whether the user asks about it or not. It also conflates instructions (system prompt) with data (tool results), making prompt engineering harder.

**Do this instead:** Let the LLM request data via function calling. The tool loop pattern ensures data is fetched on-demand and only when relevant to the user's question.

### Anti-Pattern 5: Single Giant Tool Definition

**What people do:** Create one "query_sentinel" tool that accepts a "query_type" parameter and a generic "parameters" object, trying to handle all queries through one interface.

**Why it's wrong:** The LLM performs better with specific, well-described tools. A single generic tool with a "query_type" enum gives the LLM less signal about what each query does and what parameters are meaningful. It also makes the handler a big switch statement.

**Do this instead:** Define separate tools for each query type (`query_sentinel_incidents`, `get_incident_details`, `run_kql_query`, etc.). Each tool has specific parameter schemas with descriptions. The LLM can reason about which specific tool to use based on its description.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Azure OpenAI (Chat) | `AzureOpenAI.chat.completions.create()` via openai v2.x SDK | Use `tools` parameter (not deprecated `functions`). Use `tool_choice="auto"`. Supports parallel tool calls. |
| Azure OpenAI (Embeddings) | `AzureOpenAI.embeddings.create()` via openai v2.x SDK | Use `dimensions=1024` parameter for text-embedding-3-large truncation. Rate limit: watch TPM quotas. |
| Log Analytics (KQL) | `LogsQueryClient.query_workspace()` via azure-monitor-query v2.0.0 | Returns `LogsQueryResult` or `LogsQueryPartialResult`. Always check `.status`. Supports batch queries via `query_batch()`. Set `server_timeout=600` for complex queries. |
| Sentinel REST API | Direct `requests.get/post` with bearer token from `DefaultAzureCredential` | API version `2025-09-01`. Pagination via `nextLink`/`$skipToken`. Rate limits return HTTP 429 with `Retry-After`. |
| Azure Identity | `DefaultAzureCredential()` auto-selects auth method | Supports `az login` (dev) and service principal (prod). Token caching is built-in. Create credential ONCE at startup. |
| ChromaDB | `chromadb.PersistentClient(path="./data/chroma_db")` | v1.5.0+. Zero-config local storage. Built-in metadata filtering with `where` parameter. Not suitable for concurrent multi-user access. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `main.py` <-> `openai_client.py` | Direct method calls | main passes user input, receives formatted response string |
| `openai_client.py` <-> `tool_handlers.py` | Dispatch table (dict of callables) | tool_handlers returns JSON strings; openai_client never parses them |
| `tool_handlers.py` <-> `sentinel_client.py` | Direct method calls | Handler methods map 1:1 to SentinelClient methods |
| `tool_handlers.py` <-> `vector_store.py` | Direct method calls | Handler invokes vector_store.search(), gets back formatted results |
| `openai_client.py` <-> `prompts.py` | Import constants | System prompt is a constant string; no runtime coupling |
| `openai_client.py` <-> `tools.py` | Import constants | Tool definitions are a constant list; no runtime coupling |
| `config.py` <-> all modules | Constructor injection | Config object created once, passed to all client constructors |

## Build Order (Dependency-Driven)

The following build order reflects actual code dependencies -- each phase can be built and tested independently once its dependencies are complete.

```
Phase 1: config.py
    |  (no dependencies -- pure config loading)
    |
    +-- Phase 2a: sentinel_client.py        Phase 2b: openai_client.py (chat only)
    |   (depends on: config, azure-identity, |   (depends on: config, openai SDK)
    |    azure-monitor-query)                |
    |                                        +-- tools.py (pure data, no deps)
    |                                        +-- prompts.py (pure data, no deps)
    |                                        |
    +--------------------+-------------------+
                         |
                    Phase 3: tool_handlers.py
                    (depends on: sentinel_client, vector_store)
                         |
                    Phase 3b: openai_client.py (embedding support)
                         |
                    Phase 4: vector_store.py
                    (depends on: openai_client for embeddings, chromadb)
                         |
                    Phase 5: main.py
                    (depends on: all of the above)
                         |
                    Phase 6: Integration testing + CLI polish
```

**Key parallelization opportunity:** Phases 2a (sentinel_client) and 2b (openai_client chat + tools + prompts) have no cross-dependencies and can be built simultaneously. They converge at Phase 3 (tool_handlers) which wires them together.

## Sources

- [Azure OpenAI Function Calling -- Official Microsoft Docs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/function-calling) (updated 2026-02-10) -- HIGH confidence: verified tool loop pattern, parallel function calling, tool_choice parameter, message structure
- [Azure Monitor Query Client Library for Python](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme) (azure-monitor-query v2.0.0, 2025-07-30) -- HIGH confidence: verified LogsQueryClient API, query_workspace, batch queries, response handling
- [Microsoft Sentinel REST API Reference](https://learn.microsoft.com/en-us/rest/api/securityinsights/) -- HIGH confidence: API version 2025-09-01, incident/alert endpoints
- Project INITIAL-RESEARCH.md -- HIGH confidence: comprehensive pre-existing research covering all integration points, verified against official sources
- Project PLAN.md -- HIGH confidence: existing phased build plan with dependency analysis

---
*Architecture research for: Agentic RAG Security Chatbot (Azure Sentinel + Azure OpenAI)*
*Researched: 2026-02-16*
