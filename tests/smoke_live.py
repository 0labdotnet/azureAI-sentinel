"""Live smoke test for SentinelClient against a real Sentinel workspace.

Run with: python -m tests.smoke_live

Exercises all 5 query methods with last_30d time window and Informational
severity threshold. Prints structured output showing success/failure, result
counts, and sample data for each method.

Requires: .env file with valid Azure credentials and SENTINEL_WORKSPACE_ID.
"""

import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path so `src` is importable when running directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings
from src.models import QueryError, QueryResult
from src.sentinel_client import SentinelClient


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _print_result(name: str, result: QueryResult | QueryError) -> bool:
    """Print structured result. Returns True if successful."""
    print(f"\n--- {name} ---")

    if isinstance(result, QueryError):
        print(f"  STATUS: FAILED")
        print(f"  Error code: {result.code}")
        print(f"  Message: {result.message}")
        print(f"  Retryable: {result.retry_possible}")
        return False

    meta = result.metadata
    print(f"  STATUS: OK")
    print(f"  Total: {meta.total}")
    print(f"  Query time: {meta.query_ms:.1f}ms")
    print(f"  Truncated: {meta.truncated}")
    if meta.partial_error:
        print(f"  Partial error: {meta.partial_error}")

    # Print sample data (first 3 results)
    sample_count = min(3, len(result.results))
    if sample_count > 0:
        print(f"  Sample ({sample_count} of {len(result.results)}):")
        for i, item in enumerate(result.results[:sample_count]):
            if hasattr(item, "to_dict"):
                data = item.to_dict()
            elif isinstance(item, dict):
                data = item
            else:
                data = str(item)
            print(f"    [{i+1}] {data}")
    else:
        print("  (no results -- query executed but returned empty)")

    return True


def main() -> int:
    _print_header("Sentinel Data Access Layer - Live Smoke Test")

    print("\nLoading settings from .env...")
    settings = load_settings()
    print(f"  Workspace ID: {settings.sentinel_workspace_id[:8]}...")

    print("\nCreating SentinelClient...")
    client = SentinelClient(settings)

    results = {}
    methods = [
        ("1. query_incidents(last_30d, Informational, limit=5)", lambda: client.query_incidents(time_window="last_30d", min_severity="Informational", limit=5)),
        ("2. get_incident_detail(1)", lambda: client.get_incident_detail(1)),
        ("3. query_alerts(last_30d, Informational, limit=5)", lambda: client.query_alerts(time_window="last_30d", min_severity="Informational", limit=5)),
        ("4. get_alert_trend(last_30d, Informational)", lambda: client.get_alert_trend(time_window="last_30d", min_severity="Informational")),
        ("5. get_top_entities(last_30d, Informational, limit=10)", lambda: client.get_top_entities(time_window="last_30d", min_severity="Informational", limit=10)),
    ]

    success_count = 0
    for name, method in methods:
        try:
            result = method()
            ok = _print_result(name, result)
            results[name] = ok
            if ok:
                success_count += 1
        except Exception:
            print(f"\n--- {name} ---")
            print(f"  STATUS: EXCEPTION")
            traceback.print_exc()
            results[name] = False

    _print_header("Summary")
    print(f"\n  {success_count}/{len(methods)} methods executed successfully")
    for name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    if success_count == len(methods):
        print("\n  All query methods verified against live Sentinel workspace.")
        return 0
    else:
        print(f"\n  {len(methods) - success_count} method(s) had errors -- see details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
