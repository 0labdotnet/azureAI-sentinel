"""Central KQL template registry, severity filtering, and query builder.

Merges per-domain template modules into a single TEMPLATE_REGISTRY.
Provides severity_filter() for threshold-based severity filtering,
TIME_WINDOWS for predefined time ranges, and build_query() for
validated parameter substitution.
"""

import re
from datetime import timedelta

from src.queries import alerts, entities, incidents, trends

# --------------------------------------------------------------------------
# Severity threshold model
# Sentinel has exactly four severity levels -- NO Critical.
# --------------------------------------------------------------------------

SEVERITY_ORDER = ["Informational", "Low", "Medium", "High"]


def severity_filter(min_severity: str = "Informational") -> str:
    """Return a KQL-safe comma-separated string of severity values
    at or above the given threshold.

    Examples:
        severity_filter("Medium")  -> "'Medium','High'"
        severity_filter("Informational") -> "'Informational','Low','Medium','High'"

    Invalid severity defaults to all severities (index 0).
    """
    try:
        idx = SEVERITY_ORDER.index(min_severity)
    except ValueError:
        idx = 0  # default to all severities
    included = SEVERITY_ORDER[idx:]
    return ",".join(f"'{s}'" for s in included)


# --------------------------------------------------------------------------
# Time window mapping
# Both timedelta (for API timespan param) and KQL ago() string are needed.
# --------------------------------------------------------------------------

TIME_WINDOWS: dict[str, dict] = {
    "last_1h": {"timespan": timedelta(hours=1), "kql_ago": "1h"},
    "last_24h": {"timespan": timedelta(hours=24), "kql_ago": "24h"},
    "last_3d": {"timespan": timedelta(days=3), "kql_ago": "3d"},
    "last_7d": {"timespan": timedelta(days=7), "kql_ago": "7d"},
    "last_14d": {"timespan": timedelta(days=14), "kql_ago": "14d"},
    "last_30d": {"timespan": timedelta(days=30), "kql_ago": "30d"},
}

# --------------------------------------------------------------------------
# Result limits
# --------------------------------------------------------------------------

DEFAULT_LIMITS: dict[str, int] = {
    "incident_list": 20,
    "alert_list": 20,
    "incident_detail_alerts": 50,
    "alert_trend": 365,
    "top_entities": 10,
}

MAX_LIMITS: dict[str, int] = {
    "incident_list": 100,
    "alert_list": 100,
    "incident_detail_alerts": 200,
    "alert_trend": 365,
    "top_entities": 50,
}

# --------------------------------------------------------------------------
# Per-template timeout configuration (seconds)
# Simple queries: 60s. Aggregation queries: 180s.
# --------------------------------------------------------------------------

TEMPLATE_TIMEOUTS: dict[str, int] = {
    "list_incidents": 60,
    "get_incident_by_number": 60,
    "get_incident_by_name": 60,
    "list_alerts": 60,
    "get_incident_alerts": 60,
    "get_incident_entities": 60,
    "alert_trend": 180,
    "alert_trend_total": 180,
    "top_entities": 180,
}

DEFAULT_TIMEOUT = 60

# --------------------------------------------------------------------------
# Template registry -- merged from all domain modules
# --------------------------------------------------------------------------

TEMPLATE_REGISTRY: dict[str, str] = {
    **incidents.TEMPLATES,
    **alerts.TEMPLATES,
    **trends.TEMPLATES,
    **entities.TEMPLATES,
}


def build_query(template_name: str, **params: object) -> str:
    """Build a KQL query from a named template with parameter substitution.

    Validates that the template exists and all required placeholders are provided.
    Raises ValueError for unknown templates or missing required parameters.

    Args:
        template_name: Key in TEMPLATE_REGISTRY.
        **params: Named parameters matching {placeholder} tokens in the template.

    Returns:
        The rendered KQL query string.
    """
    if template_name not in TEMPLATE_REGISTRY:
        raise ValueError(
            f"Unknown template: '{template_name}'. "
            f"Available: {sorted(TEMPLATE_REGISTRY.keys())}"
        )

    template = TEMPLATE_REGISTRY[template_name]

    # Extract required placeholders from the template
    # Match {name} but not {{escaped}} patterns
    placeholders = set(re.findall(r"\{(\w+)\}", template))

    # Check for missing required params
    missing = placeholders - set(params.keys())
    if missing:
        raise ValueError(
            f"Missing required parameters for '{template_name}': {sorted(missing)}"
        )

    return template.format(**params)
