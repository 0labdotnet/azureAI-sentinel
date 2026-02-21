"""Tests for the CLI chat loop (run_chat)."""

from unittest.mock import MagicMock, patch

from src.main import run_chat


class TestQuitCommand:
    """Test /quit exits cleanly."""

    def test_quit_exits(self, mock_env_vars):
        with (
            patch("builtins.input", return_value="/quit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()  # Should exit without error


class TestExitCommand:
    """Test /exit exits cleanly."""

    def test_exit_exits(self, mock_env_vars):
        with (
            patch("builtins.input", return_value="/exit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()  # Should exit without error


class TestClearCommand:
    """Test /clear calls session.clear()."""

    def test_clear_calls_session(self, mock_env_vars):
        inputs = iter(["/clear", "/quit"])

        mock_session_instance = MagicMock()
        mock_session_instance.clear.return_value = "Summary text"

        with (
            patch("builtins.input", side_effect=inputs),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession", return_value=mock_session_instance),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()

        mock_session_instance.clear.assert_called_once()


class TestSendMessage:
    """Test that user input is forwarded to session.send_message."""

    def test_forwards_message(self, mock_env_vars):
        inputs = iter(["hello", "/quit"])

        mock_session_instance = MagicMock()
        mock_session_instance.send_message.return_value = "Hi there!"

        with (
            patch("builtins.input", side_effect=inputs),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession", return_value=mock_session_instance),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()

        mock_session_instance.send_message.assert_called_once_with("hello")


class TestKeyboardInterrupt:
    """Test Ctrl+C exits cleanly."""

    def test_keyboard_interrupt_exits(self, mock_env_vars):
        with (
            patch("builtins.input", side_effect=KeyboardInterrupt),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()  # Should exit without traceback


class TestKnowledgeBaseStartup:
    """Test that run_chat initializes knowledge base and prints status."""

    def test_prints_kb_unavailable_when_init_returns_none(
        self, mock_env_vars, capsys
    ):
        with (
            patch("builtins.input", return_value="/quit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
            patch("src.main._init_knowledge_base", return_value=None),
        ):
            run_chat()

        captured = capsys.readouterr()
        assert "Knowledge base unavailable" in captured.err

    def test_passes_vector_store_to_chat_session(self, mock_env_vars):
        mock_vs = MagicMock()

        with (
            patch("builtins.input", return_value="/quit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession") as mock_session_cls,
            patch("src.main._init_knowledge_base", return_value=mock_vs),
        ):
            run_chat()

        # Verify ChatSession was called with vector_store kwarg
        call_kwargs = mock_session_cls.call_args[1]
        assert call_kwargs["vector_store"] is mock_vs
