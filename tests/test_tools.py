"""Tests for OpenAI tool definitions in src/tools.py."""

from src.queries import SEVERITY_ORDER, TIME_WINDOWS
from src.tools import SENTINEL_TOOLS, get_tool_names

EXPECTED_TOOL_NAMES = [
    "query_incidents",
    "get_incident_detail",
    "query_alerts",
    "get_alert_trend",
    "get_top_entities",
]

# Severity enum in display order (High first) -- reverse of SEVERITY_ORDER
EXPECTED_SEVERITY_ENUM = ["High", "Medium", "Low", "Informational"]


class TestToolDefinitions:
    """Test SENTINEL_TOOLS structure and content."""

    def test_tool_count(self):
        assert len(SENTINEL_TOOLS) == 5

    def test_tool_names_match_expected(self):
        names = [t["function"]["name"] for t in SENTINEL_TOOLS]
        assert names == EXPECTED_TOOL_NAMES

    def test_each_tool_has_function_type(self):
        for tool in SENTINEL_TOOLS:
            assert tool["type"] == "function"

    def test_each_tool_has_required_keys(self):
        for tool in SENTINEL_TOOLS:
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_no_tool_has_strict_true(self):
        """Critical: strict mode is incompatible with parallel tool calls."""
        for tool in SENTINEL_TOOLS:
            assert tool.get("strict") is not True
            assert tool["function"].get("strict") is not True

    def test_time_window_enum_matches_time_windows_keys(self):
        """time_window enums should match TIME_WINDOWS keys."""
        expected_enum = sorted(TIME_WINDOWS.keys())
        # Check tools that have time_window parameter
        tools_with_time_window = [
            "query_incidents",
            "query_alerts",
            "get_alert_trend",
            "get_top_entities",
        ]
        for tool in SENTINEL_TOOLS:
            name = tool["function"]["name"]
            if name in tools_with_time_window:
                props = tool["function"]["parameters"]["properties"]
                tw = props["time_window"]
                assert sorted(tw["enum"]) == expected_enum, (
                    f"{name}: time_window enum mismatch"
                )

    def test_severity_enum_matches_severity_order(self):
        """min_severity enums should match SEVERITY_ORDER in reverse."""
        expected = list(reversed(SEVERITY_ORDER))
        assert expected == EXPECTED_SEVERITY_ENUM
        # Check tools that have min_severity parameter
        tools_with_severity = [
            "query_incidents",
            "query_alerts",
            "get_alert_trend",
            "get_top_entities",
        ]
        for tool in SENTINEL_TOOLS:
            name = tool["function"]["name"]
            if name in tools_with_severity:
                props = tool["function"]["parameters"]["properties"]
                sev = props["min_severity"]
                assert sev["enum"] == EXPECTED_SEVERITY_ENUM, (
                    f"{name}: severity enum mismatch"
                )

    def test_query_incidents_required_params(self):
        tool = _get_tool("query_incidents")
        assert tool["function"]["parameters"]["required"] == [
            "time_window"
        ]

    def test_get_incident_detail_required_params(self):
        tool = _get_tool("get_incident_detail")
        assert tool["function"]["parameters"]["required"] == [
            "incident_ref"
        ]

    def test_query_alerts_required_params(self):
        tool = _get_tool("query_alerts")
        assert tool["function"]["parameters"]["required"] == [
            "time_window"
        ]

    def test_get_alert_trend_required_params(self):
        tool = _get_tool("get_alert_trend")
        assert tool["function"]["parameters"]["required"] == [
            "time_window"
        ]

    def test_get_top_entities_required_params(self):
        tool = _get_tool("get_top_entities")
        assert tool["function"]["parameters"]["required"] == [
            "time_window"
        ]


class TestGetToolNames:
    """Test the get_tool_names() helper."""

    def test_returns_correct_names(self):
        assert get_tool_names() == EXPECTED_TOOL_NAMES

    def test_returns_list_of_strings(self):
        names = get_tool_names()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_returns_five_names(self):
        assert len(get_tool_names()) == 5


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _get_tool(name: str) -> dict:
    """Look up a tool definition by function name."""
    for tool in SENTINEL_TOOLS:
        if tool["function"]["name"] == name:
            return tool
    raise ValueError(f"Tool not found: {name}")
