"""KQL templates for alert trend analysis queries.

Trend queries use summarize + bin() for time-series bucketing.
These are aggregation queries that require 180s server_timeout.

IMPORTANT: SecurityAlert uses AlertSeverity, NOT Severity.
"""

TEMPLATES = {
    "alert_trend": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | summarize Count=count() by bin(TimeGenerated, {bin_size}), AlertSeverity
        | order by TimeGenerated asc
    """,
    "alert_trend_total": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | summarize Count=count() by bin(TimeGenerated, {bin_size})
        | order by TimeGenerated asc
    """,
}
