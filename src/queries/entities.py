"""KQL templates for entity ranking queries.

Entity queries use parse_json + mv-expand to extract entities from
SecurityAlert.Entities JSON column, then aggregate by entity type/name.
These are aggregation queries that require 180s server_timeout.

IMPORTANT: SecurityAlert uses AlertSeverity, NOT Severity.
Entity types are lowercase: "account", "ip", "host".
"""

TEMPLATES = {
    "top_entities": """
        SecurityAlert
        | where TimeGenerated > ago({time_range})
        | where AlertSeverity in ({severity_filter})
        | extend EntitiesParsed = parse_json(Entities)
        | mv-expand Entity = EntitiesParsed
        | extend EntityType = tostring(Entity.Type),
                 EntityName = case(
                     Entity.Type == "account", tostring(Entity.Name),
                     Entity.Type == "ip", tostring(Entity.Address),
                     Entity.Type == "host", tostring(Entity.HostName),
                     tostring(Entity.Name)
                 )
        | where isnotempty(EntityName)
        | where EntityType in ("account", "ip", "host")
        | summarize AlertCount=count(), Severities=make_set(AlertSeverity)
            by EntityType, EntityName
        | order by AlertCount desc
        | take {limit}
    """,
}
