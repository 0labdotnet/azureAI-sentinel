"""Tool dispatch handler for routing OpenAI tool calls to SentinelClient methods.

Provides ToolDispatcher which maps tool names to SentinelClient methods,
handles argument extraction with sensible defaults, and implements silent
single-retry on retryable errors.
"""

import contextlib
import logging

from src.models import QueryError
from src.sentinel_client import SentinelClient

logger = logging.getLogger(__name__)

# Status messages shown to the user while a tool executes
_STATUS_MESSAGES: dict[str, str] = {
    "query_incidents": "Querying incidents...",
    "get_incident_detail": "Looking up incident details...",
    "query_alerts": "Querying alerts...",
    "get_alert_trend": "Analyzing alert trends...",
    "get_top_entities": "Finding top targeted entities...",
}

_DEFAULT_STATUS = "Processing query..."


class ToolDispatcher:
    """Routes tool calls to SentinelClient methods with retry logic.

    Each tool name maps 1:1 to a SentinelClient method. Unknown tool names
    return a structured error dict. Retryable errors are retried once silently
    before returning the error.
    """

    def __init__(self, sentinel_client: SentinelClient):
        self._client = sentinel_client
        self._dispatch_map: dict[str, callable] = {
            "query_incidents": self._query_incidents,
            "get_incident_detail": self._get_incident_detail,
            "query_alerts": self._query_alerts,
            "get_alert_trend": self._get_alert_trend,
            "get_top_entities": self._get_top_entities,
        }

    def dispatch(self, tool_name: str, arguments: dict) -> dict:
        """Dispatch a tool call. Returns a dict suitable for JSON serialization.

        - Unknown tool names return {"error": "Unknown tool: {name}"}
        - Retryable errors are retried once silently
        - All results come from .to_dict() on QueryResult/QueryError
        """
        handler = self._dispatch_map.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}

        return handler(arguments)

    def get_status_message(self, tool_name: str) -> str:
        """Return a user-facing status message for tool execution."""
        return _STATUS_MESSAGES.get(tool_name, _DEFAULT_STATUS)

    # ------------------------------------------------------------------
    # Private: retry wrapper
    # ------------------------------------------------------------------

    def _call_with_retry(self, method, *args, **kwargs) -> dict:
        """Call a SentinelClient method, retrying once on retryable errors.

        Returns the .to_dict() serialization of the final result.
        """
        result = method(*args, **kwargs)

        # Check if retryable error -- retry once silently
        if isinstance(result, QueryError) and result.retry_possible:
            logger.debug("Retryable error on %s, retrying once", method.__name__)
            result = method(*args, **kwargs)

        return result.to_dict()

    # ------------------------------------------------------------------
    # Private: individual tool handlers
    # ------------------------------------------------------------------

    def _query_incidents(self, args: dict) -> dict:
        time_window = args.get("time_window", "last_24h")
        min_severity = args.get("min_severity", "Informational")
        limit = args.get("limit", 20)
        return self._call_with_retry(
            self._client.query_incidents,
            time_window=time_window,
            min_severity=min_severity,
            limit=limit,
        )

    def _get_incident_detail(self, args: dict) -> dict:
        incident_ref = args.get("incident_ref")
        if incident_ref is None:
            return {"error": "Missing required parameter: incident_ref"}

        # Convert numeric strings to int for exact number lookup
        if isinstance(incident_ref, str):
            with contextlib.suppress(ValueError, TypeError):
                incident_ref = int(incident_ref)

        return self._call_with_retry(
            self._client.get_incident_detail,
            incident_ref=incident_ref,
        )

    def _query_alerts(self, args: dict) -> dict:
        time_window = args.get("time_window", "last_24h")
        min_severity = args.get("min_severity", "Informational")
        limit = args.get("limit", 20)
        return self._call_with_retry(
            self._client.query_alerts,
            time_window=time_window,
            min_severity=min_severity,
            limit=limit,
        )

    def _get_alert_trend(self, args: dict) -> dict:
        time_window = args.get("time_window", "last_7d")
        min_severity = args.get("min_severity", "Informational")
        bin_size = args.get("bin_size")
        return self._call_with_retry(
            self._client.get_alert_trend,
            time_window=time_window,
            min_severity=min_severity,
            bin_size=bin_size,
        )

    def _get_top_entities(self, args: dict) -> dict:
        time_window = args.get("time_window", "last_7d")
        min_severity = args.get("min_severity", "Informational")
        limit = args.get("limit", 10)
        return self._call_with_retry(
            self._client.get_top_entities,
            time_window=time_window,
            min_severity=min_severity,
            limit=limit,
        )
