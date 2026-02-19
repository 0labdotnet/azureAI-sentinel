"""Tests for system prompts and templates in src/prompts.py."""

from src.prompts import (
    CLEAR_SUMMARY_TEMPLATE,
    DISCLAIMER,
    MAX_ROUNDS_MESSAGE,
    SYSTEM_PROMPT,
    TOKEN_WARNING,
)


class TestSystemPrompt:
    """Test SYSTEM_PROMPT content requirements."""

    def test_is_non_empty_string(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_contains_grounding_rule(self):
        """Must contain no-fabrication or context-poisoning language."""
        lower = SYSTEM_PROMPT.lower()
        assert "fabricat" in lower or "context poisoning" in lower

    def test_contains_context_poisoning_guard(self):
        """Must explicitly refuse example/sample data."""
        assert "context poisoning" in SYSTEM_PROMPT.lower()

    def test_contains_transparency_instruction(self):
        """Must contain footnote/data-sources transparency."""
        lower = SYSTEM_PROMPT.lower()
        assert (
            "data sources" in lower
            or "footnote" in lower
            or "tools were called" in lower
        )

    def test_contains_numbered_reference_instruction(self):
        """Must instruct numbered [1], [2], [3] result format."""
        assert "[1]" in SYSTEM_PROMPT or "[2]" in SYSTEM_PROMPT

    def test_contains_human_verification_caveat(self):
        """Must include human analyst verification requirement."""
        lower = SYSTEM_PROMPT.lower()
        assert "human analyst" in lower or "verified" in lower

    def test_contains_role_definition(self):
        lower = SYSTEM_PROMPT.lower()
        assert "security operations" in lower or "sentinel" in lower

    def test_contains_tool_guidance(self):
        lower = SYSTEM_PROMPT.lower()
        assert "query_incidents" in lower or "tool" in lower


class TestTemplateConstants:
    """Test auxiliary prompt template constants."""

    def test_token_warning_is_non_empty(self):
        assert isinstance(TOKEN_WARNING, str)
        assert len(TOKEN_WARNING) > 0

    def test_max_rounds_message_is_non_empty(self):
        assert isinstance(MAX_ROUNDS_MESSAGE, str)
        assert len(MAX_ROUNDS_MESSAGE) > 0

    def test_clear_summary_template_is_non_empty(self):
        assert isinstance(CLEAR_SUMMARY_TEMPLATE, str)
        assert len(CLEAR_SUMMARY_TEMPLATE) > 0

    def test_disclaimer_contains_verification(self):
        lower = DISCLAIMER.lower()
        assert "verified" in lower or "human analyst" in lower
