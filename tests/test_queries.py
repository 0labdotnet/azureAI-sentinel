"""Tests for KQL template registry, severity filter, and query builder."""

from datetime import timedelta

import pytest

from src.queries import (
    DEFAULT_LIMITS,
    MAX_LIMITS,
    TEMPLATE_REGISTRY,
    TEMPLATE_TIMEOUTS,
    TIME_WINDOWS,
    build_query,
    severity_filter,
)


class TestSeverityFilter:
    """Tests for severity_filter() threshold model."""

    def test_informational_returns_all(self):
        """Informational threshold should include all four severity levels."""
        result = severity_filter("Informational")
        assert result == "'Informational','Low','Medium','High'"

    def test_low_returns_low_and_above(self):
        """Low threshold should include Low, Medium, High."""
        result = severity_filter("Low")
        assert result == "'Low','Medium','High'"

    def test_medium_returns_medium_and_above(self):
        """Medium threshold should include Medium, High."""
        result = severity_filter("Medium")
        assert result == "'Medium','High'"

    def test_high_returns_high_only(self):
        """High threshold should include only High."""
        result = severity_filter("High")
        assert result == "'High'"

    def test_invalid_defaults_to_all(self):
        """Invalid severity input should default to all severities."""
        result = severity_filter("Critical")
        assert result == "'Informational','Low','Medium','High'"

    def test_empty_string_defaults_to_all(self):
        """Empty string should default to all severities."""
        result = severity_filter("")
        assert result == "'Informational','Low','Medium','High'"

    def test_default_parameter(self):
        """Default parameter should be Informational (all severities)."""
        result = severity_filter()
        assert result == "'Informational','Low','Medium','High'"


class TestTimeWindows:
    """Tests for TIME_WINDOWS configuration."""

    def test_expected_keys_present(self):
        """TIME_WINDOWS should contain all expected window names."""
        expected = {"last_1h", "last_24h", "last_3d", "last_7d", "last_14d", "last_30d"}
        assert set(TIME_WINDOWS.keys()) == expected

    def test_timedelta_and_kql_ago_pairs(self):
        """Each window should have matching timedelta and kql_ago values."""
        assert TIME_WINDOWS["last_1h"]["timespan"] == timedelta(hours=1)
        assert TIME_WINDOWS["last_1h"]["kql_ago"] == "1h"

        assert TIME_WINDOWS["last_24h"]["timespan"] == timedelta(hours=24)
        assert TIME_WINDOWS["last_24h"]["kql_ago"] == "24h"

        assert TIME_WINDOWS["last_7d"]["timespan"] == timedelta(days=7)
        assert TIME_WINDOWS["last_7d"]["kql_ago"] == "7d"

        assert TIME_WINDOWS["last_30d"]["timespan"] == timedelta(days=30)
        assert TIME_WINDOWS["last_30d"]["kql_ago"] == "30d"

    def test_each_window_has_both_fields(self):
        """Every time window should have both timespan and kql_ago."""
        for name, window in TIME_WINDOWS.items():
            assert "timespan" in window, f"{name} missing timespan"
            assert "kql_ago" in window, f"{name} missing kql_ago"
            assert isinstance(window["timespan"], timedelta), f"{name} timespan is not timedelta"
            assert isinstance(window["kql_ago"], str), f"{name} kql_ago is not str"


class TestTemplateRegistry:
    """Tests for TEMPLATE_REGISTRY completeness."""

    def test_contains_all_expected_templates(self):
        """Registry should contain all templates across 4 domain modules."""
        expected = {
            "list_incidents",
            "get_incident_by_number",
            "get_incident_by_name",
            "get_incident_alerts",
            "get_incident_entities",
            "list_alerts",
            "alert_trend",
            "alert_trend_total",
            "top_entities",
        }
        assert expected.issubset(set(TEMPLATE_REGISTRY.keys()))

    def test_template_count(self):
        """Registry should have exactly 9 templates across 4 domain modules."""
        assert len(TEMPLATE_REGISTRY) == 9


class TestBuildQuery:
    """Tests for build_query() parameter substitution."""

    def test_renders_template_with_params(self):
        """build_query should substitute all named parameters."""
        query = build_query(
            "list_incidents",
            time_range="24h",
            severity_filter="'Medium','High'",
            limit=20,
        )
        assert "24h" in query
        assert "'Medium','High'" in query
        assert "20" in query
        # Should still contain KQL keywords
        assert "SecurityIncident" in query
        assert "arg_max" in query

    def test_raises_for_unknown_template(self):
        """build_query should raise ValueError for unknown template names."""
        with pytest.raises(ValueError, match="Unknown template: 'nonexistent'"):
            build_query("nonexistent", time_range="24h")

    def test_raises_for_missing_params(self):
        """build_query should raise ValueError for missing required parameters."""
        with pytest.raises(ValueError, match="Missing required parameters"):
            build_query("list_incidents", time_range="24h")
            # Missing severity_filter and limit

    def test_incident_by_number_template(self):
        """get_incident_by_number should render with incident_number param."""
        query = build_query("get_incident_by_number", incident_number=42)
        assert "42" in query
        assert "IncidentNumber == 42" in query

    def test_incident_by_name_template(self):
        """get_incident_by_name should render with incident_name and limit."""
        query = build_query(
            "get_incident_by_name",
            incident_name="phishing",
            limit=10,
        )
        assert 'contains "phishing"' in query
        assert "take 10" in query


class TestTemplateTimeouts:
    """Tests for TEMPLATE_TIMEOUTS configuration."""

    def test_simple_queries_have_60s_timeout(self):
        """Simple lookup queries should have 60s timeout."""
        simple_templates = [
            "list_incidents",
            "get_incident_by_number",
            "get_incident_by_name",
            "list_alerts",
            "get_incident_alerts",
            "get_incident_entities",
        ]
        for name in simple_templates:
            assert TEMPLATE_TIMEOUTS[name] == 60, f"{name} should have 60s timeout"

    def test_aggregation_queries_have_180s_timeout(self):
        """Aggregation queries should have 180s timeout."""
        agg_templates = ["alert_trend", "alert_trend_total", "top_entities"]
        for name in agg_templates:
            assert TEMPLATE_TIMEOUTS[name] == 180, f"{name} should have 180s timeout"


class TestLimits:
    """Tests for DEFAULT_LIMITS and MAX_LIMITS."""

    def test_default_limits_values(self):
        assert DEFAULT_LIMITS["incident_list"] == 20
        assert DEFAULT_LIMITS["alert_list"] == 20
        assert DEFAULT_LIMITS["incident_detail_alerts"] == 50
        assert DEFAULT_LIMITS["top_entities"] == 10

    def test_max_limits_values(self):
        assert MAX_LIMITS["incident_list"] == 100
        assert MAX_LIMITS["alert_list"] == 100
        assert MAX_LIMITS["incident_detail_alerts"] == 200
        assert MAX_LIMITS["top_entities"] == 50

    def test_max_always_gte_default(self):
        """MAX_LIMITS should always be >= DEFAULT_LIMITS for matching keys."""
        for key in DEFAULT_LIMITS:
            if key in MAX_LIMITS:
                assert MAX_LIMITS[key] >= DEFAULT_LIMITS[key], (
                    f"MAX_LIMITS[{key}] < DEFAULT_LIMITS[{key}]"
                )
