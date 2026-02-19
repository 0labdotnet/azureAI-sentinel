"""Tests for the CLI chat loop (run_chat)."""

from unittest.mock import MagicMock, patch

import pytest

from src.main import run_chat


class TestQuitCommand:
    """Test /quit exits cleanly."""

    def test_quit_exits(self, mock_env_vars):
        with (
            patch("builtins.input", return_value="/quit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
        ):
            run_chat()  # Should exit without error


class TestExitCommand:
    """Test /exit exits cleanly."""

    def test_exit_exits(self, mock_env_vars):
        with (
            patch("builtins.input", return_value="/exit"),
            patch("src.main.SentinelClient"),
            patch("src.main.ChatSession"),
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
        ):
            run_chat()  # Should exit without traceback
