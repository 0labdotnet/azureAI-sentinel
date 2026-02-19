# Phase 3: AI Orchestration & Integration - Research

**Researched:** 2026-02-19
**Domain:** OpenAI tool calling loop, tool dispatch, multi-turn conversation management, grounded responses
**Confidence:** HIGH

## Summary

Phase 3 builds the AI orchestration layer: the OpenAI client, tool definitions mapping to the existing SentinelClient, the agentic tool-calling loop, conversation memory with token management, and the system prompt that enforces grounding and safety rules. The existing Phase 2 codebase provides a clean SentinelClient with 5 query methods that return typed QueryResult/QueryError objects with `.to_dict()` serialization -- perfectly suited as tool backends.

The core technical pattern is straightforward: a `while` loop that calls `chat.completions.create`, checks for `tool_calls` in the response, executes them against SentinelClient, appends results as `role: "tool"` messages, and loops until the model returns a text response (no more tool calls) or MAX_TOOL_ROUNDS is reached. The OpenAI SDK v2.x, `AzureOpenAI` client, and `tools` parameter are all well-documented and stable.

**Primary recommendation:** Use the standard Chat Completions API with `AzureOpenAI` client (already in requirements.txt), `tools` parameter (not deprecated `functions`), and a simple while-loop for the tool-calling agent. Enable parallel tool calls (the default for gpt-4o) but do NOT use `strict: true` on tool schemas -- these two features are incompatible per official Microsoft docs. Instead, validate tool arguments defensively in the handler layer, which gpt-4o handles reliably in practice.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Conversation flow
- Support both implicit references ("tell me more about that incident") and numbered references ([1], [2], [3]) in result lists -- users will naturally use both
- Default conversation memory window: 30 turns, configurable in settings (will tune experimentally for token/context balance)
- When approaching token limit: warn the user ("Context getting long, older messages will be trimmed"), then truncate oldest messages
- On /clear: preserve user preferences and generate a summary of key discussion items that carries forward as condensed context -- user doesn't completely lose session context

#### Response style
- Default verbosity: explanatory -- present data with brief context and interpretation (not terse, not verbose walkthrough)
- Reasoning transparency: footnote style -- answer first, then a section below listing which tools were called and what data was retrieved
- Data formatting: basic readable tables in Phase 3 -- rich formatting, color-coding, and severity indicators added in Phase 5
- Follow-up suggestions: only when helpful for complex results (e.g., incident lists), not after every response

#### Tool invocation UX
- Simple text status messages during tool execution in Phase 3 (e.g., "Querying incidents...") -- spinners and progress bars in Phase 5
- Error handling: retry silently once on failure, then explain the error clearly with actionable suggestions if retry also fails
- Parallel tool calls: yes, when the question warrants it (e.g., broad queries that benefit from concurrent incident + alert queries)
- MAX_TOOL_ROUNDS = 5: only surface the limit when reached ("Reached maximum tool rounds. Here's what I found so far.")
- Max tool rounds configurable in settings but not exposed in user-facing UI

#### Grounding & safety
- Data presentation: facts first from tool results, then offer deeper analysis as opt-in ("Would you like me to analyze potential implications?") with human-verification disclaimer
- Empty results: state clearly, then suggest alternatives (broaden severity, expand time range)
- Out-of-scope questions: explain what the chatbot CAN do, keep it friendly with business-appropriate humor -- light jokes and puns encouraged; nothing crude, violent, sexual, racist, or otherwise distasteful
- **Hard rule: never fabricate data.** No synthetic incident numbers, severities, timestamps, or example data under any circumstances. If asked for examples, respond: "I'm not allowed to provide example data to prevent context poisoning. Let me query some real data..."
- All AI-generated analysis must carry a disclaimer that it should be verified by a human before taking action

### Claude's Discretion
- Exact system prompt wording and personality tuning
- Token budget allocation strategy across conversation turns
- Specific retry logic implementation (exponential backoff, etc.)
- How the /clear summary is structured internally
- Loading skeleton / waiting state phrasing

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ORCH-01 | User can have multi-turn conversations where the chatbot remembers prior context (e.g., "tell me more about that incident" after an incident list) | Conversation history management via messages list, token counting with tiktoken, 30-turn sliding window, numbered result references in system prompt instructions |
| ORCH-02 | All factual claims in chatbot responses are grounded in tool call results -- the chatbot never fabricates incident numbers, severities, or timestamps | System prompt with hard grounding rules, tool result injection as `role: "tool"` messages, no-fabrication instruction in system prompt, context poisoning framing |
| ORCH-03 | Chatbot explains its reasoning by describing which tools it used and what data it found before answering | System prompt instructs footnote-style transparency, tool call tracking in the orchestrator for metadata passed back to user, tool execution log maintained per turn |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | >=2.21.0 | AzureOpenAI client, chat.completions.create with tools | Already in requirements.txt; official SDK for Azure OpenAI |
| tiktoken | >=0.12.0 | Token counting for conversation management | Official OpenAI tokenizer; o200k_base encoding for gpt-4o |
| azure-identity | >=1.25.0 | DefaultAzureCredential for auth | Already in requirements.txt |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | - | Parse tool_call arguments, serialize tool results | Every tool call round |
| asyncio (stdlib) | - | Concurrent execution of multiple tool calls | When model returns parallel tool_calls |
| logging (stdlib) | - | Tool execution logging, error tracking | All tool handler operations |

### NOT Adding
| Library | Reason |
|---------|--------|
| langchain | Locked decision: direct OpenAI SDK, no orchestration frameworks |
| openai-agents | Overkill for POC; adds complexity without proportional benefit |
| pydantic | Not needed for tool schemas; use raw dicts matching OpenAI format |

**Installation (add to requirements.txt):**
```bash
pip install tiktoken>=0.12.0
```

Note: `openai`, `azure-identity`, and `rich` are already in requirements.txt.

## Architecture Patterns

### Recommended Project Structure (New files for Phase 3)
```
src/
├── openai_client.py       # ChatClient wrapping AzureOpenAI
├── tools.py               # Tool schema definitions (JSON dicts)
├── tool_handlers.py       # Dispatcher: tool name -> SentinelClient method
├── prompts.py             # System prompt and prompt templates
├── conversation.py        # ConversationManager: history, token budget, /clear
├── orchestrator.py        # Main agent loop: chat -> tool calls -> results -> chat
├── config.py              # (EXISTING) Add max_tool_rounds, max_turns to Settings
├── sentinel_client.py     # (EXISTING) No changes needed
├── models.py              # (EXISTING) No changes needed
├── queries/               # (EXISTING) No changes needed
└── projections.py         # (EXISTING) No changes needed
```

### Pattern 1: Agentic Tool Loop
**What:** A while loop that repeatedly calls the LLM, processes tool calls, and sends results back until the model produces a final text response or the round limit is hit.
**When to use:** Every user message goes through this loop.
**Example:**
```python
# Source: Microsoft Learn - Azure OpenAI Function Calling (2026-02-10)
# Adapted for multi-round agentic loop with MAX_TOOL_ROUNDS

import json
from openai import AzureOpenAI

def run_tool_loop(client, messages, tools, tool_handlers, max_rounds=5):
    """Execute the agentic tool-calling loop.

    Returns:
        tuple: (final_response_content, tool_log)
        tool_log is a list of dicts recording which tools were called and results.
    """
    tool_log = []

    for round_num in range(max_rounds):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        messages.append(response_message)  # Append assistant message (may have tool_calls)

        # If no tool calls, we have the final answer
        if not response_message.tool_calls:
            return response_message.content, tool_log

        # Process each tool call
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # Execute tool via handler
            result = tool_handlers.dispatch(function_name, function_args)
            result_str = json.dumps(result)

            # Append tool result to messages
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result_str,
            })

            # Track for transparency reporting
            tool_log.append({
                "tool": function_name,
                "args": function_args,
                "result_summary": _summarize_result(result),
            })

    # Hit max rounds -- return whatever we have
    return None, tool_log  # Caller handles the "max rounds reached" message
```

### Pattern 2: Tool Schema Definitions
**What:** Tool definitions as JSON dicts matching the OpenAI `tools` parameter format.
**When to use:** Passed to every `chat.completions.create` call.
**Example:**
```python
# Source: Microsoft Learn - Azure OpenAI Function Calling (2026-02-10)
# Note: NOT using strict: true because it is incompatible with parallel tool calls.
# gpt-4o is reliable enough for these simple schemas without strict mode.

SENTINEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_incidents",
            "description": "Query Microsoft Sentinel for security incidents filtered by severity and time range. Returns a list of incidents with number, title, severity, status, and timestamps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": ["last_1h", "last_24h", "last_3d", "last_7d", "last_14d", "last_30d"],
                        "description": "Time range to search. Use 'last_24h' for recent, 'last_7d' for weekly view."
                    },
                    "min_severity": {
                        "type": "string",
                        "enum": ["High", "Medium", "Low", "Informational"],
                        "description": "Minimum severity threshold. 'High' returns only High. 'Medium' returns Medium and High."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of incidents to return. Default 20, max 100."
                    }
                },
                "required": ["time_window"],
            }
        }
    },
    # ... similar for get_incident_detail, query_alerts, get_alert_trend, get_top_entities
]
```

### Pattern 3: Conversation Memory with Token Budget
**What:** Maintain conversation history as a list of message dicts, count tokens with tiktoken, truncate oldest messages when approaching the context limit.
**When to use:** Before every LLM call, validate the token budget.
**Example:**
```python
# Source: OpenAI Cookbook - How to Count Tokens with Tiktoken
import tiktoken

class ConversationManager:
    """Manages conversation history with token-aware truncation."""

    # gpt-4o context: 128K tokens. Reserve space for:
    # - System prompt: ~2000 tokens
    # - Tool definitions: ~1500 tokens
    # - Current response: ~4000 tokens
    # - Safety margin: ~500 tokens
    MAX_HISTORY_TOKENS = 120_000  # Conservative limit
    WARNING_THRESHOLD = 100_000   # Warn user at this level

    def __init__(self, max_turns=30):
        self.max_turns = max_turns
        self.messages = []  # Does NOT include system prompt
        self.encoding = tiktoken.encoding_for_model("gpt-4o")

    def count_tokens(self, messages):
        """Count tokens for a list of messages using o200k_base encoding."""
        num_tokens = 0
        for message in messages:
            num_tokens += 3  # tokens_per_message for gpt-4o
            for key, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(self.encoding.encode(value))
                if key == "name":
                    num_tokens += 1
        num_tokens += 3  # reply priming
        return num_tokens

    def add_and_trim(self, message):
        """Add a message and trim oldest if needed."""
        self.messages.append(message)

        # Trim by turn count
        while len(self.messages) > self.max_turns * 2:  # *2 for user+assistant pairs
            self.messages.pop(0)

        # Trim by token budget
        while self.count_tokens(self.messages) > self.MAX_HISTORY_TOKENS:
            self.messages.pop(0)
```

### Pattern 4: Tool Handler Dispatch
**What:** Maps tool call names to SentinelClient methods, handles argument validation, error wrapping, and retry.
**When to use:** Called from the tool loop for each tool_call.
**Example:**
```python
class ToolHandler:
    """Dispatches tool calls to SentinelClient methods with retry."""

    def __init__(self, sentinel_client):
        self._client = sentinel_client
        self._dispatch_map = {
            "query_incidents": self._query_incidents,
            "get_incident_detail": self._get_incident_detail,
            "query_alerts": self._query_alerts,
            "get_alert_trend": self._get_alert_trend,
            "get_top_entities": self._get_top_entities,
        }

    def dispatch(self, tool_name, args):
        """Execute a tool call. Returns dict suitable for JSON serialization."""
        handler = self._dispatch_map.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        # First attempt
        result = handler(args)
        if isinstance(result, dict) and result.get("error") and result.get("retry_possible"):
            # Silent retry once per user decision
            result = handler(args)

        return result

    def _query_incidents(self, args):
        result = self._client.query_incidents(
            time_window=args.get("time_window", "last_24h"),
            min_severity=args.get("min_severity", "Informational"),
            limit=args.get("limit", 20),
        )
        return result.to_dict()  # Both QueryResult and QueryError have .to_dict()
```

### Anti-Patterns to Avoid
- **Appending raw response objects:** Always append `response.choices[0].message` (the message object), not the full response. The message object includes `tool_calls` which the API needs in subsequent calls.
- **Using `role: "function"` instead of `role: "tool"`:** The `function` role is deprecated and causes infinite loops where the model keeps calling the same tool.
- **Mixing strict mode with parallel tool calls:** `strict: true` in tool schemas is incompatible with `parallel_tool_calls`. Since the user requires parallel tool calls, do NOT use strict mode. Validate arguments defensively instead.
- **Forgetting tool_call_id:** Every `role: "tool"` message MUST include `tool_call_id` matching the `id` from the corresponding `tool_call` in the assistant's response. Omitting this causes API errors.
- **Sending tool definitions in the second call:** After all tool results are appended, the follow-up `chat.completions.create` call should still include `tools` (the model may decide to call more tools in subsequent rounds).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token counting | String length estimation or word counting | `tiktoken` with `o200k_base` encoding | Token != word; tiktoken uses the exact BPE tokenizer the model uses |
| JSON argument parsing | Custom string parsing | `json.loads(tool_call.function.arguments)` | OpenAI guarantees JSON-parseable arguments (even without strict mode, gpt-4o is >99% reliable) |
| Conversation serialization | Custom message format | Standard OpenAI message dicts (role/content/tool_call_id) | The API requires this exact format; deviating causes errors |
| Retry with backoff | Sleep + manual counter | `tenacity` library or simple for-loop (1 retry per user decision) | User decided: retry once silently, then report. Simple enough for a loop. |

**Key insight:** The OpenAI Chat Completions API defines the exact message format. The tool loop is mechanically simple -- the complexity is in the system prompt, conversation management, and error handling, not in the API plumbing.

## Common Pitfalls

### Pitfall 1: strict: true + parallel_tool_calls Incompatibility
**What goes wrong:** If you set `strict: true` in tool schemas AND allow parallel tool calls (the default for gpt-4o), the API may produce errors or the model may not generate parallel calls. Microsoft's official documentation explicitly states: "Structured outputs are not supported with parallel function calls. When using structured outputs set parallel_tool_calls to false."
**Why it happens:** Structured Outputs uses constrained decoding that cannot handle generating multiple tool calls simultaneously.
**How to avoid:** Do NOT use `strict: true` on tool schemas. gpt-4o generates reliable arguments without strict mode for simple schemas like ours (enum fields, basic types). Validate arguments defensively in the handler layer.
**Warning signs:** Tool calls never come in parallel; single tool calls only despite multi-part queries.

### Pitfall 2: Azure OpenAI parallel_tool_calls Parameter
**What goes wrong:** Historically, Azure OpenAI's API returned "Unknown parameter: 'parallel_tool_calls'" when explicitly setting this parameter via the `AzureOpenAI` client with versioned API endpoints.
**Why it happens:** Azure's API version lag behind OpenAI's native API. The newer v1 endpoint (`/openai/v1/`) and recent API versions may have resolved this.
**How to avoid:** Do NOT explicitly set `parallel_tool_calls=True` (it is already the default for gpt-4o). Simply omit the parameter. The model will naturally generate parallel tool calls when appropriate. If you need to disable parallel calls in the future, test with your specific API version first.
**Warning signs:** 400 errors mentioning "Unknown parameter".

### Pitfall 3: Token Budget Explosion from Tool Results
**What goes wrong:** Large Sentinel query results (e.g., 100 incidents with full details) consume massive token budgets, leaving little room for conversation history.
**Why it happens:** Each `role: "tool"` message with JSON results is tokenized and added to the message history. Sentinel data can be verbose.
**How to avoid:** (1) Projections are already applied in SentinelClient (Phase 2) -- this helps. (2) Limit default result counts (20 incidents, not 100). (3) Consider summarizing tool results if they exceed a token threshold before adding to history. (4) Count tokens AFTER adding tool results, not just user messages.
**Warning signs:** Token count warnings appearing after a single query round; context truncation happening within one exchange.

### Pitfall 4: Conversation History Breaks After Tool Calls
**What goes wrong:** If you don't append the assistant message containing `tool_calls` before appending `role: "tool"` results, the API returns an error about orphaned tool results.
**Why it happens:** The message sequence must be: assistant (with tool_calls) -> tool (result 1) -> tool (result 2) -> ... The API validates this sequence.
**How to avoid:** Always `messages.append(response_message)` BEFORE iterating over `response_message.tool_calls` to append results.
**Warning signs:** API errors about invalid message sequence or unexpected tool role messages.

### Pitfall 5: Infinite Tool Call Loops
**What goes wrong:** The model keeps calling tools round after round without ever producing a final text response.
**Why it happens:** Ambiguous prompts, overly aggressive tool descriptions, or the system prompt not instructing the model when to stop calling tools and synthesize.
**How to avoid:** (1) MAX_TOOL_ROUNDS = 5 as a hard cap. (2) System prompt explicitly instructs: "After gathering sufficient data, synthesize your findings into a response. Do not call additional tools unless the data is insufficient." (3) Include a round counter in the loop.
**Warning signs:** Consistently hitting MAX_TOOL_ROUNDS on simple queries.

### Pitfall 6: Token Counting Inaccuracy for Tool Definitions
**What goes wrong:** The basic `num_tokens_from_messages()` function does not account for tool definitions, which are injected into the system message by the API and consume additional tokens.
**Why it happens:** Tool definitions are serialized using internal formatting that adds overhead tokens (approximately 7 tokens per function + 3 per property + additional for enums).
**How to avoid:** Use the `num_tokens_for_tools()` function from the OpenAI cookbook, or add a generous safety buffer (~2000 tokens) when computing available context space.
**Warning signs:** Token limit errors despite your counting showing sufficient headroom.

## Code Examples

### OpenAI Client Setup (AzureOpenAI)
```python
# Source: INITIAL-RESEARCH.md Section 3.2, verified against existing config.py
from openai import AzureOpenAI
from src.config import Settings

class ChatClient:
    """Wraps AzureOpenAI for chat completions with tools."""

    def __init__(self, settings: Settings):
        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,  # "2024-10-21"
        )
        self._model = settings.azure_openai_chat_deployment  # "gpt-4o"

    def chat(self, messages, tools=None, tool_choice="auto"):
        """Send chat completion request. Returns the response object."""
        kwargs = {
            "model": self._model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return self._client.chat.completions.create(**kwargs)
```

### Tool Result Message Format
```python
# Source: Microsoft Learn - Azure OpenAI Function Calling (2026-02-10)
# CRITICAL: Each tool result MUST include tool_call_id matching the assistant's tool_call.id

# After receiving response with tool_calls:
response_message = response.choices[0].message
messages.append(response_message)  # MUST append assistant message first

for tool_call in response_message.tool_calls:
    result = dispatch_tool(tool_call.function.name,
                           json.loads(tool_call.function.arguments))
    messages.append({
        "tool_call_id": tool_call.id,    # REQUIRED: matches tool_call.id
        "role": "tool",                   # REQUIRED: must be "tool", NOT "function"
        "name": tool_call.function.name,  # Optional but recommended
        "content": json.dumps(result),    # REQUIRED: must be a string
    })
```

### Token Counting for gpt-4o
```python
# Source: OpenAI Cookbook - How to Count Tokens with Tiktoken
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4o")  # Returns o200k_base

def count_message_tokens(messages):
    """Count tokens for gpt-4o chat messages."""
    tokens_per_message = 3  # Verified for gpt-4o-2024-08-06
    tokens_per_name = 1
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            if isinstance(value, str):
                num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # Reply priming
    return num_tokens
```

### Parallel Tool Execution with asyncio
```python
# For executing multiple tool calls concurrently (I/O bound Sentinel queries)
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def execute_tools_parallel(tool_calls, handler):
    """Execute multiple tool calls concurrently using thread pool.

    SentinelClient uses synchronous azure-monitor-query SDK,
    so we run in threads rather than native async.
    """
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=5)

    tasks = []
    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        task = loop.run_in_executor(executor, handler.dispatch, name, args)
        tasks.append((tool_call, task))

    results = []
    for tool_call, task in tasks:
        result = await task
        results.append((tool_call, result))

    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `functions` / `function_call` params | `tools` / `tool_choice` params | API version 2023-12-01-preview | Must use `tools` -- `functions` is deprecated |
| openai v1.x | openai v2.x | September 2025 | Project already targets v2.x (>=2.21.0) |
| `cl100k_base` encoding | `o200k_base` encoding | gpt-4o launch (2024) | tiktoken.encoding_for_model("gpt-4o") returns o200k_base |
| Assistants API | Responses API | 2025-2026 migration | Not relevant for POC; Chat Completions API remains fully supported |
| AzureOpenAI versioned endpoint | OpenAI v1 endpoint (`/openai/v1/`) | August 2025 | Both work; stick with AzureOpenAI client + api_version for consistency with existing code |
| Single tool calls only | Parallel tool calls default | API version 2023-12-01-preview | gpt-4o generates parallel calls by default; handle multiple tool_calls per response |

**Deprecated/outdated:**
- `functions` / `function_call` parameters: Replaced by `tools` / `tool_choice`. Using the old params causes the model to use `role: "function"` responses, leading to infinite loops.
- Assistants API: Being sunset in favor of Responses API. Not relevant; we use Chat Completions.

## Open Questions

1. **Azure API version and parallel_tool_calls**
   - What we know: The `parallel_tool_calls` parameter historically caused errors on Azure OpenAI. The default behavior for gpt-4o is to make parallel calls when appropriate.
   - What's unclear: Whether api_version 2024-10-21 (our configured version) properly supports the `parallel_tool_calls` parameter, or if we must rely on the default behavior.
   - Recommendation: Do NOT explicitly set `parallel_tool_calls`. Let the default behavior work. If we need to disable it later, test first with the specific API version.

2. **Token counting accuracy with tool definitions**
   - What we know: Tool definitions add ~7 tokens per function + overhead. The basic `num_tokens_from_messages()` does not account for this.
   - What's unclear: Exact overhead for our specific 5-tool schema set.
   - Recommendation: Calculate tool definition tokens once at startup, subtract from available budget as a fixed cost. Add 500-token safety margin.

3. **Tool result size limits**
   - What we know: Sentinel queries can return large result sets. Projections reduce size.
   - What's unclear: Average token count for typical tool results (e.g., 20 incidents).
   - Recommendation: Measure empirically during implementation. Set soft limits on result serialization size (~4000 tokens per tool result) and truncate with a "... showing first N of M results" note if exceeded.

## Sources

### Primary (HIGH confidence)
- [Microsoft Learn - Azure OpenAI Function Calling](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/function-calling) - Complete Python examples for tool calling, parallel calls, verified 2026-02-10
- [Microsoft Learn - Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) - strict: true incompatibility with parallel_tool_calls, verified 2026-02-11
- [OpenAI Cookbook - How to Count Tokens with Tiktoken](https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken/) - Token counting functions for gpt-4o, o200k_base encoding
- [OpenAI Function Calling Guide](https://developers.openai.com/api/docs/guides/function-calling/) - Tool definition schema, multi-turn loop pattern, parallel calls
- Existing codebase: src/config.py, src/sentinel_client.py, src/models.py, src/queries/__init__.py -- verified interface contracts

### Secondary (MEDIUM confidence)
- [tiktoken on PyPI](https://pypi.org/project/tiktoken/) - v0.12.0, o200k_base encoding
- [openai-python GitHub](https://github.com/openai/openai-python) - SDK v2.x, AzureOpenAI client
- [Azure OpenAI parallel_tool_calls issue #1492](https://github.com/openai/openai-python/issues/1492) - Historical Azure parameter support issue

### Tertiary (LOW confidence)
- [OpenAI Community - Tool Call Loops](https://community.openai.com/t/chat-completion-api-tool-call-loops/887083) - Community patterns for loop termination

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - openai v2.x and tiktoken are well-documented, already in project
- Architecture (tool loop pattern): HIGH - Microsoft's own examples show the exact pattern
- Architecture (conversation management): MEDIUM - Token counting is well-documented but conversation truncation strategies are implementation-specific
- Pitfalls: HIGH - strict/parallel incompatibility verified from official Microsoft docs
- System prompt design: MEDIUM - Best practices documented but effectiveness requires experimentation

**Research date:** 2026-02-19
**Valid until:** 2026-03-19 (stable APIs, unlikely to change)
