"""Tests for ChatSession: tool loop, conversation management, and trimming."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.openai_client import ChatSession, _summarize_result


class TestSendMessageSimple:
    """Test basic send_message without tool calls."""

    def test_returns_text_content(self, mock_settings, mock_openai_client, mock_sentinel_client):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )
        result = session.send_message("hello")

        assert result == "Test response"

    def test_conversation_history_has_two_messages(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )
        session.send_message("hello")

        # Should have user message + assistant message
        user_msgs = [m for m in session._messages if m["role"] == "user"]
        assistant_msgs = [m for m in session._messages if m["role"] == "assistant"]
        assert len(user_msgs) == 1
        assert len(assistant_msgs) == 1
        assert user_msgs[0]["content"] == "hello"
        assert assistant_msgs[0]["content"] == "Test response"


class TestSendMessageWithToolCall:
    """Test send_message when the LLM requests tool calls."""

    @pytest.fixture
    def tool_call_client(self):
        """Mock client that returns tool calls on first call, text on second."""
        client = MagicMock()

        # First call: tool call response
        tool_call_msg = MagicMock()
        tool_call_msg.content = None

        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_001"
        mock_tool_call.function.name = "query_incidents"
        mock_tool_call.function.arguments = json.dumps({"time_window": "last_24h"})
        tool_call_msg.tool_calls = [mock_tool_call]

        first_choice = MagicMock()
        first_choice.message = tool_call_msg
        first_response = MagicMock()
        first_response.choices = [first_choice]

        # Second call: text response
        text_msg = MagicMock()
        text_msg.content = "Here are your incidents..."
        text_msg.tool_calls = None

        second_choice = MagicMock()
        second_choice.message = text_msg
        second_response = MagicMock()
        second_response.choices = [second_choice]

        client.chat.completions.create.side_effect = [first_response, second_response]
        return client

    def test_dispatches_tool_and_returns_final_response(
        self, mock_settings, tool_call_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=tool_call_client,
            sentinel_client=mock_sentinel_client,
        )

        # Mock the dispatcher to return a known result
        with patch.object(session._dispatcher, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = {
                "metadata": {"total": 3, "query_ms": 45.0, "truncated": False},
                "results": [{"number": 1, "title": "Test Incident"}],
            }

            result = session.send_message("show me incidents")

        assert result == "Here are your incidents..."
        mock_dispatch.assert_called_once_with(
            "query_incidents", {"time_window": "last_24h"}
        )


class TestToolLoopMaxRounds:
    """Test that the tool loop terminates after max_tool_rounds."""

    def test_terminates_after_max_rounds(self, mock_settings, mock_sentinel_client):
        """Mock client that always returns tool calls, verifying loop termination."""
        client = MagicMock()

        # Create a tool call response that always has tool_calls
        def make_tool_response():
            msg = MagicMock()
            msg.content = None
            tc = MagicMock()
            tc.id = "call_loop"
            tc.function.name = "query_incidents"
            tc.function.arguments = json.dumps({"time_window": "last_24h"})
            msg.tool_calls = [tc]
            choice = MagicMock()
            choice.message = msg
            resp = MagicMock()
            resp.choices = [choice]
            return resp

        # Final summarization response (after max rounds)
        final_msg = MagicMock()
        final_msg.content = "Summary after max rounds"
        final_msg.tool_calls = None
        final_choice = MagicMock()
        final_choice.message = final_msg
        final_response = MagicMock()
        final_response.choices = [final_choice]

        # max_tool_rounds=5 tool responses + 1 final summarization
        responses = [make_tool_response() for _ in range(5)]
        responses.append(final_response)
        client.chat.completions.create.side_effect = responses

        mock_settings.max_tool_rounds = 5
        session = ChatSession(
            mock_settings,
            client=client,
            sentinel_client=mock_sentinel_client,
        )

        with patch.object(session._dispatcher, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"metadata": {"total": 0, "query_ms": 10.0}}

            result = session.send_message("infinite loop test")

        assert result == "Summary after max rounds"
        # 5 rounds of tool calls + 1 final summary = 6 total API calls
        assert client.chat.completions.create.call_count == 6


class TestConversationHistory:
    """Test that conversation history is preserved across messages."""

    def test_history_preserved_across_messages(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )

        session.send_message("first message")
        session.send_message("second message")

        # Second API call should include both user messages and first assistant response
        second_call_args = mock_openai_client.chat.completions.create.call_args_list[1]
        messages = second_call_args[1]["messages"]

        # messages[0] is system prompt
        assert messages[0]["role"] == "system"
        # messages[1] is first user message
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "first message"
        # messages[2] is first assistant response
        assert messages[2]["role"] == "assistant"
        # messages[3] is second user message
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "second message"


class TestTurnTrimming:
    """Test conversation trimming at the max_turns boundary."""

    def test_trims_oldest_messages(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        mock_settings.max_turns = 2
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )

        session.send_message("message 1")
        session.send_message("message 2")
        session.send_message("message 3")

        # After 3 turns with max_turns=2, oldest messages should be trimmed
        user_msgs = [m for m in session._messages if m["role"] == "user"]
        # Should not contain "message 1" anymore
        user_contents = [m["content"] for m in user_msgs]
        assert "message 1" not in user_contents
        assert "message 3" in user_contents


class TestClear:
    """Test the clear() method."""

    def test_clear_with_summary(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        # First call: normal send_message response
        # Second call: summary generation response
        normal_msg = MagicMock()
        normal_msg.content = "Test response"
        normal_msg.tool_calls = None
        normal_choice = MagicMock()
        normal_choice.message = normal_msg
        normal_response = MagicMock()
        normal_response.choices = [normal_choice]

        summary_msg = MagicMock()
        summary_msg.content = "User discussed incidents."
        summary_choice = MagicMock()
        summary_choice.message = summary_msg
        summary_response = MagicMock()
        summary_response.choices = [summary_choice]

        mock_openai_client.chat.completions.create.side_effect = [
            normal_response,
            summary_response,
        ]

        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )

        session.send_message("show me incidents")
        summary = session.clear()

        assert summary == "User discussed incidents."
        assert session.get_history_length() == 0
        # Messages should contain only the preserved summary context
        assert len(session._messages) == 1
        assert "Previous session context" in session._messages[0]["content"]

    def test_clear_empty_conversation(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )

        result = session.clear()

        assert result == "Nothing to clear."


class TestParallelToolCalls:
    """Test handling of multiple tool calls in a single response."""

    def test_dispatches_both_tool_calls(self, mock_settings, mock_sentinel_client):
        client = MagicMock()

        # First call: response with 2 tool calls
        tool_msg = MagicMock()
        tool_msg.content = None

        tc1 = MagicMock()
        tc1.id = "call_001"
        tc1.function.name = "query_incidents"
        tc1.function.arguments = json.dumps({"time_window": "last_24h"})

        tc2 = MagicMock()
        tc2.id = "call_002"
        tc2.function.name = "get_alert_trend"
        tc2.function.arguments = json.dumps({"time_window": "last_7d"})

        tool_msg.tool_calls = [tc1, tc2]

        first_choice = MagicMock()
        first_choice.message = tool_msg
        first_response = MagicMock()
        first_response.choices = [first_choice]

        # Second call: text response
        text_msg = MagicMock()
        text_msg.content = "Here is an overview with trends."
        text_msg.tool_calls = None
        second_choice = MagicMock()
        second_choice.message = text_msg
        second_response = MagicMock()
        second_response.choices = [second_choice]

        client.chat.completions.create.side_effect = [first_response, second_response]

        session = ChatSession(
            mock_settings,
            client=client,
            sentinel_client=mock_sentinel_client,
        )

        with patch.object(session._dispatcher, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = {"metadata": {"total": 5, "query_ms": 30.0}}

            result = session.send_message("overview with trends")

        assert result == "Here is an overview with trends."
        assert mock_dispatch.call_count == 2

        # Verify both tool results are in messages
        tool_msgs = [m for m in session._messages if m["role"] == "tool"]
        assert len(tool_msgs) == 2
        assert tool_msgs[0]["tool_call_id"] == "call_001"
        assert tool_msgs[1]["tool_call_id"] == "call_002"


class TestGetHistoryLength:
    """Test get_history_length method."""

    def test_returns_turn_count(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )

        assert session.get_history_length() == 0

        session.send_message("hello")
        assert session.get_history_length() == 1


class TestSummarizeResult:
    """Test the _summarize_result helper."""

    def test_query_result_format(self):
        result = {"metadata": {"total": 5, "query_ms": 123.456}}
        assert _summarize_result(result) == "5 results, 123ms"

    def test_error_format(self):
        result = {"error": "Unknown tool: foo", "message": "Unknown tool: foo"}
        assert _summarize_result(result) == "Error: Unknown tool: foo"

    def test_error_without_message(self):
        result = {"error": "something went wrong"}
        assert _summarize_result(result) == "Error: something went wrong"

    def test_empty_dict(self):
        result = {}
        assert _summarize_result(result) == "OK"


class TestChatSessionWithVectorStore:
    """Test ChatSession tool list behavior with/without VectorStore."""

    def test_with_vector_store_includes_kb_tools(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        mock_vs = MagicMock()
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
            vector_store=mock_vs,
        )
        # Should have 5 Sentinel + 3 KB = 8 tools
        assert len(session._tools) == 8

        # Verify tools are passed to the API call
        session.send_message("test")
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert len(call_kwargs["tools"]) == 8

    def test_without_vector_store_sentinel_only(
        self, mock_settings, mock_openai_client, mock_sentinel_client
    ):
        session = ChatSession(
            mock_settings,
            client=mock_openai_client,
            sentinel_client=mock_sentinel_client,
        )
        # Should have only 5 Sentinel tools
        assert len(session._tools) == 5

        # Verify tools are passed to the API call
        session.send_message("test")
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert len(call_kwargs["tools"]) == 5
