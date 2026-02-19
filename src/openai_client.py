"""ChatSession for Azure OpenAI with tool calling and conversation management.

Combines the AzureOpenAI client wrapper, agentic tool-calling loop (max
MAX_TOOL_ROUNDS iterations), conversation history with turn-based trimming
(max MAX_TURNS), and tool usage tracking for transparency reporting.
"""

import json
import logging
import sys

from openai import AzureOpenAI

from src.config import Settings
from src.prompts import (
    CLEAR_SUMMARY_TEMPLATE,
    MAX_ROUNDS_MESSAGE,
    SYSTEM_PROMPT,
    TOKEN_WARNING,
)
from src.sentinel_client import SentinelClient
from src.tool_handlers import ToolDispatcher
from src.tools import SENTINEL_TOOLS

logger = logging.getLogger(__name__)


class ChatSession:
    """Manages a chat session with Azure OpenAI including tool calling and conversation history.

    Combines:
    - AzureOpenAI client wrapper
    - Agentic tool-calling loop (max MAX_TOOL_ROUNDS iterations)
    - Conversation history with turn-based trimming (max MAX_TURNS)
    - Tool usage tracking for transparency reporting
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: AzureOpenAI | None = None,
        sentinel_client: SentinelClient | None = None,
    ):
        """Initialize ChatSession.

        Args:
            settings: Application settings.
            client: Optional AzureOpenAI client (for test injection).
            sentinel_client: Optional SentinelClient (for test injection).
        """
        self._settings = settings
        self._model = settings.azure_openai_chat_deployment
        self._max_tool_rounds = settings.max_tool_rounds
        self._max_turns = settings.max_turns

        # Client setup -- accept injected clients for testing
        if client is not None:
            self._client = client
        else:
            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )

        if sentinel_client is not None:
            self._sentinel_client = sentinel_client
        else:
            self._sentinel_client = SentinelClient(settings)

        self._dispatcher = ToolDispatcher(self._sentinel_client)

        # Conversation state (does NOT include system prompt -- that is prepended on each call)
        self._messages: list[dict] = []
        self._turn_count: int = 0

    def send_message(self, user_input: str) -> str:
        """Send a user message and get an assistant response, running tools as needed.

        Args:
            user_input: The user's natural language question or command.

        Returns:
            The assistant's final text response.
        """
        # Append user message
        self._messages.append({"role": "user", "content": user_input})
        self._turn_count += 1

        # Check if trimming is needed
        if self._turn_count > self._max_turns:
            print(TOKEN_WARNING, file=sys.stderr)
            self._trim_messages()

        # Build full message list with system prompt prepended
        full_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._messages,
        ]

        # Tool loop
        tool_log: list[dict] = []
        for _round in range(self._max_tool_rounds):
            response = self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                tools=SENTINEL_TOOLS,
                tool_choice="auto",
            )

            response_message = response.choices[0].message

            # Append assistant message BEFORE tool results (critical per research)
            assistant_msg = {"role": "assistant", "content": response_message.content}
            if response_message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response_message.tool_calls
                ]
            self._messages.append(assistant_msg)

            # If no tool calls, we have the final answer
            if not response_message.tool_calls:
                break

            # Process each tool call
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name

                # Print status message to stderr
                print(
                    self._dispatcher.get_status_message(tool_name),
                    file=sys.stderr,
                )

                # Parse arguments and dispatch
                parsed_args = json.loads(tool_call.function.arguments)
                result = self._dispatcher.dispatch(tool_name, parsed_args)

                # Append tool result to messages
                self._messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": json.dumps(result),
                    }
                )

                # Track in tool log
                tool_log.append(
                    {
                        "tool": tool_name,
                        "args": parsed_args,
                        "result_preview": _summarize_result(result),
                    }
                )

            # Update full_messages for next iteration
            full_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self._messages,
            ]
        else:
            # Hit max_tool_rounds without a text response
            # Append a message asking the model to summarize what it found
            self._messages.append(
                {"role": "user", "content": MAX_ROUNDS_MESSAGE}
            )
            full_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self._messages,
            ]
            response = self._client.chat.completions.create(
                model=self._model,
                messages=full_messages,
            )
            response_message = response.choices[0].message
            self._messages.append(
                {"role": "assistant", "content": response_message.content}
            )

        # Return the last assistant message content
        for msg in reversed(self._messages):
            if msg["role"] == "assistant" and msg.get("content"):
                return msg["content"]

        return ""

    def _trim_messages(self) -> None:
        """Remove oldest messages to stay within max_turns limit.

        Removes messages from the front in safe chunks, avoiding splitting
        an assistant message with tool_calls from its corresponding tool
        result messages. Finds the first 'user' message boundary and removes
        everything before the next 'user' message.
        """
        target_len = self._max_turns * 2

        while len(self._messages) > target_len:
            # Find the index of the second "user" message -- remove everything before it
            user_indices = [
                i
                for i, m in enumerate(self._messages)
                if m["role"] == "user"
            ]

            if len(user_indices) < 2:
                # Can't safely trim further
                break

            # Remove everything before the second user message
            cut_index = user_indices[1]
            self._messages = self._messages[cut_index:]

    def clear(self) -> str:
        """Clear conversation history, preserving a summary.

        Returns:
            Summary text of the cleared conversation, or a message if nothing to clear.
        """
        if not self._messages:
            return "Nothing to clear."

        # Build a summary request using the current conversation
        summary_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *self._messages,
            {"role": "user", "content": CLEAR_SUMMARY_TEMPLATE},
        ]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=summary_messages,
        )

        summary = response.choices[0].message.content or "Session cleared."

        # Reset messages but preserve summary as prior context
        self._messages = [
            {
                "role": "assistant",
                "content": f"Previous session context: {summary}",
            }
        ]
        self._turn_count = 0

        return summary

    def get_history_length(self) -> int:
        """Return current turn count."""
        return self._turn_count


def _summarize_result(result: dict) -> str:
    """Create a brief text summary of a tool result for logging.

    For QueryResult-shaped dicts: "{total} results, {query_ms}ms".
    For error dicts: "Error: {message}".
    """
    if "error" in result:
        return f"Error: {result.get('message', result.get('error', 'unknown'))}"

    metadata = result.get("metadata", {})
    if metadata:
        total = metadata.get("total", 0)
        query_ms = metadata.get("query_ms", 0)
        return f"{total} results, {query_ms:.0f}ms"

    return "OK"
