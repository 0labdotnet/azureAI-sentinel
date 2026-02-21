"""OpenAI tool definitions for Sentinel query functions.

Defines SENTINEL_TOOLS in the OpenAI `tools` parameter format,
mapping 1:1 to SentinelClient public query methods. No strict mode
is used (incompatible with parallel tool calls).
"""

SENTINEL_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "query_incidents",
            "description": (
                "Query Microsoft Sentinel security incidents "
                "filtered by time range and severity. "
                "Use this for questions about recent incidents, "
                "incident lists, 'what's happening', "
                "'show me incidents', or general security status "
                "overviews. Returns incident number, "
                "title, severity, status, and timestamps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": [
                            "last_1h",
                            "last_24h",
                            "last_3d",
                            "last_7d",
                            "last_14d",
                            "last_30d",
                        ],
                        "description": (
                            "Time range to query. Use 'last_24h' "
                            "for recent activity, wider ranges "
                            "for historical views."
                        ),
                    },
                    "min_severity": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low",
                            "Informational",
                        ],
                        "description": (
                            "Minimum severity threshold. 'High' "
                            "returns only high-severity incidents, "
                            "'Informational' returns all."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Maximum number of incidents to return."
                            " Default 20, max 100."
                        ),
                    },
                },
                "required": ["time_window"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_incident_detail",
            "description": (
                "Get detailed information about a specific "
                "incident including description, alerts, "
                "entities, timeline, and classification. "
                "Use this for 'tell me about incident X', "
                "'details on incident 42', drill-downs on "
                "specific incidents, or when the user "
                "references a previous result by number. "
                "Pass an integer for exact incident number "
                "lookup, or a string for case-insensitive "
                "title search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "incident_ref": {
                        "type": "string",
                        "description": (
                            "Incident reference: an incident "
                            "number (e.g. '42') for exact lookup, "
                            "or a text string (e.g. 'phishing') "
                            "for case-insensitive title search."
                        ),
                    },
                },
                "required": ["incident_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_alerts",
            "description": (
                "Query Microsoft Sentinel security alerts "
                "filtered by time range and severity. "
                "Alerts are individual detection signals, "
                "distinct from incidents which group "
                "related alerts. Use this for questions "
                "specifically about alerts, detection signals, "
                "or 'show me alerts'. For grouped security "
                "events, use query_incidents instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": [
                            "last_1h",
                            "last_24h",
                            "last_3d",
                            "last_7d",
                            "last_14d",
                            "last_30d",
                        ],
                        "description": "Time range to query.",
                    },
                    "min_severity": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low",
                            "Informational",
                        ],
                        "description": (
                            "Minimum severity threshold."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Maximum number of alerts to return."
                            " Default 20, max 100."
                        ),
                    },
                },
                "required": ["time_window"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alert_trend",
            "description": (
                "Get alert volume trends bucketed by time "
                "intervals over a configurable period. "
                "Use this for trend analysis, pattern "
                "detection, 'how have alerts changed', "
                "'is there an increase in alerts', or "
                "temporal pattern questions. Returns "
                "time-series data with alert counts "
                "per time bucket."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": [
                            "last_1h",
                            "last_24h",
                            "last_3d",
                            "last_7d",
                            "last_14d",
                            "last_30d",
                        ],
                        "description": (
                            "Time range to analyze trends over."
                        ),
                    },
                    "min_severity": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low",
                            "Informational",
                        ],
                        "description": (
                            "Minimum severity threshold."
                        ),
                    },
                    "bin_size": {
                        "type": "string",
                        "description": (
                            "Time bucket granularity: '1h' for "
                            "hourly or '1d' for daily. "
                            "Auto-selected if omitted based on "
                            "time window."
                        ),
                    },
                },
                "required": ["time_window"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_entities",
            "description": (
                "Get the most frequently targeted entities "
                "(users, IP addresses, hosts) ranked by "
                "alert count. Use this for 'who is being "
                "targeted', 'most attacked', 'top entities', "
                "'most common attackers', or entity-focused "
                "security questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {
                        "type": "string",
                        "enum": [
                            "last_1h",
                            "last_24h",
                            "last_3d",
                            "last_7d",
                            "last_14d",
                            "last_30d",
                        ],
                        "description": "Time range to query.",
                    },
                    "min_severity": {
                        "type": "string",
                        "enum": [
                            "High",
                            "Medium",
                            "Low",
                            "Informational",
                        ],
                        "description": (
                            "Minimum severity threshold."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Maximum number of entities to return."
                            " Default 10, max 50."
                        ),
                    },
                },
                "required": ["time_window"],
            },
        },
    },
]


KB_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_similar_incidents",
            "description": (
                "Search for similar historical incidents in the "
                "knowledge base. Use this when the user asks "
                "'have we seen this before?', 'similar attacks', "
                "'historical incidents like X', or wants to know "
                "if a pattern has occurred previously."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the "
                            "incident or attack pattern to search for."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_playbooks",
            "description": (
                "Search for investigation and response playbooks "
                "in the knowledge base. Use this when the user "
                "asks 'how to investigate X', 'response procedure "
                "for Y', 'investigation guidance', or wants "
                "step-by-step instructions for handling an "
                "incident type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the "
                            "investigation topic or incident type "
                            "to find playbooks for."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_investigation_guidance",
            "description": (
                "Get MITRE ATT&CK-mapped investigation guidance "
                "combining playbooks and historical context. "
                "Use this when the user asks about 'MITRE "
                "techniques', 'ATT&CK mappings', 'what techniques "
                "are involved in X', or wants technique-based "
                "recommendations for investigating an attack."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the "
                            "attack or technique to get guidance for."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def get_tool_names() -> list[str]:
    """Return the list of all tool function names."""
    return [
        tool["function"]["name"]
        for tool in SENTINEL_TOOLS + KB_TOOLS
    ]
