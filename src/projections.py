"""Per-query-type field projection configurations.

Projections define which fields are included in each view of query results.
Templates return full rows; projections are applied post-query in Python to
filter fields for LLM consumption.

entity_count is included in both incident_list and incident_detail projections
per user decision. In list view it will be 0 (no cross-table join); in detail
view it is populated from the entity sub-query results.
"""

PROJECTIONS: dict[str, list[str]] = {
    "incident_list": [
        "number",
        "title",
        "severity",
        "status",
        "created_time",
        "alert_count",
        "entity_count",
        "last_modified_time",
        "created_time_ago",
        "last_modified_time_ago",
    ],
    "incident_detail": [
        "number",
        "title",
        "severity",
        "status",
        "description",
        "created_time",
        "last_modified_time",
        "closed_time",
        "owner",
        "alert_count",
        "entity_count",
        "labels",
        "classification",
        "classification_reason",
        "first_activity_time",
        "last_activity_time",
        "incident_url",
        "created_time_ago",
        "last_modified_time_ago",
    ],
    "alert_list": [
        "name",
        "display_name",
        "severity",
        "status",
        "time_generated",
        "tactics",
        "provider_name",
        "compromised_entity",
        "time_generated_ago",
    ],
}


def apply_projection(data: dict, view: str) -> dict:
    """Filter a dict to only include keys present in the projection for the given view.

    Returns the unmodified dict if the view is not found in PROJECTIONS (defensive).

    Args:
        data: The full data dict (e.g., from dataclass.to_dict()).
        view: The projection view name (e.g., "incident_list").

    Returns:
        A new dict containing only the projected fields.
    """
    if view not in PROJECTIONS:
        return data
    allowed = set(PROJECTIONS[view])
    return {k: v for k, v in data.items() if k in allowed}
