"""KQL templates for SecurityAlert queries.

IMPORTANT: SecurityAlert uses AlertSeverity, NOT Severity.
This is a known pitfall -- the column name differs from SecurityIncident.
"""

TEMPLATES = {
    "list_alerts": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | project AlertName, DisplayName, AlertSeverity, Status,
                  TimeGenerated, Description, Tactics, Techniques,
                  ProviderName, CompromisedEntity, SystemAlertId
        | order by TimeGenerated desc
        | take {limit}
    """,
}
