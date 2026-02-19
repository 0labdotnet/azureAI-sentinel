"""KQL templates for SecurityIncident queries.

Templates use named placeholders for parameter substitution via build_query().
SecurityIncident logs a new row on every modification, so all queries use
summarize arg_max(LastModifiedTime, *) by IncidentNumber for deduplication.
"""

TEMPLATES = {
    "list_incidents": """
        SecurityIncident
        | where TimeGenerated > ago({time_range})
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | where Severity in ({severity_filter})
        | project IncidentNumber, Title, Severity, Status, CreatedTime,
                  LastModifiedTime, Owner, AlertIds, Description,
                  FirstActivityTime, LastActivityTime
        | order by CreatedTime desc
        | take {limit}
    """,
    "get_incident_by_number": """
        SecurityIncident
        | where IncidentNumber == {incident_number}
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | project IncidentNumber, Title, Severity, Status, Description,
                  CreatedTime, LastModifiedTime, ClosedTime, Owner,
                  AlertIds, Labels, Classification, ClassificationReason,
                  FirstActivityTime, LastActivityTime, IncidentUrl
    """,
    "get_incident_by_name": """
        SecurityIncident
        | summarize arg_max(LastModifiedTime, *) by IncidentNumber
        | where Title contains "{incident_name}"
        | project IncidentNumber, Title, Severity, Status, Description,
                  CreatedTime, LastModifiedTime, ClosedTime, Owner,
                  AlertIds, Labels, Classification, ClassificationReason,
                  FirstActivityTime, LastActivityTime, IncidentUrl
        | take {limit}
    """,
    "get_incident_alerts": """
        let incident_alerts = SecurityIncident
            | where IncidentNumber == {incident_number}
            | summarize arg_max(LastModifiedTime, *) by IncidentNumber
            | mv-expand AlertId = AlertIds
            | project tostring(AlertId);
        SecurityAlert
        | where SystemAlertId in (incident_alerts)
        | project AlertName, DisplayName, AlertSeverity, Status,
                  TimeGenerated, Description, Tactics, Techniques,
                  ProviderName, CompromisedEntity, SystemAlertId
    """,
    "get_incident_entities": """
        let incident_alerts = SecurityIncident
            | where IncidentNumber == {incident_number}
            | summarize arg_max(LastModifiedTime, *) by IncidentNumber
            | mv-expand AlertId = AlertIds
            | project tostring(AlertId);
        SecurityAlert
        | where SystemAlertId in (incident_alerts)
        | extend EntitiesParsed = parse_json(Entities)
        | mv-expand Entity = EntitiesParsed
        | extend EntityType = tostring(Entity.Type),
                 EntityName = case(
                     Entity.Type == "account", tostring(Entity.Name),
                     Entity.Type == "ip", tostring(Entity.Address),
                     Entity.Type == "host", tostring(Entity.HostName),
                     Entity.Type == "url", tostring(Entity.Url),
                     Entity.Type == "file", tostring(Entity.Name),
                     tostring(Entity.Name)
                 )
        | where isnotempty(EntityName)
        | distinct EntityType, EntityName
    """,
}
