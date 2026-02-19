"""Configuration module with layered validation and connectivity checks.

Provides Settings dataclass, environment variable validation, and Azure service
connectivity testing with content-filter-specific error detection.
"""

import os
import sys
from dataclasses import dataclass
from datetime import timedelta

import openai
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from dotenv import load_dotenv
from openai import AzureOpenAI
from rich.console import Console
from rich.table import Table


@dataclass
class Settings:
    """All configuration loaded from environment variables."""

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"

    # Sentinel / Log Analytics
    sentinel_workspace_id: str = ""

    # Auth (optional -- DefaultAzureCredential handles this via az login)
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Internal tuning knobs (not loaded from env vars)
    max_tool_rounds: int = 5
    max_turns: int = 30


# Phase 1 required vars -- later phases add to this
REQUIRED_VARS: dict[str, str] = {
    "AZURE_OPENAI_ENDPOINT": "Azure OpenAI endpoint URL",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI API key",
    "SENTINEL_WORKSPACE_ID": "Log Analytics workspace GUID",
}

# Phase 2+ optional vars -- noted as "not yet needed"
OPTIONAL_VARS: dict[str, str] = {
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "Embedding model deployment (Phase 4)",
    "CHROMADB_PATH": "ChromaDB storage path (Phase 4)",
}


def load_settings() -> Settings:
    """Load and return settings from .env file."""
    load_dotenv()
    return Settings(
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_openai_chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o"),
        azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        sentinel_workspace_id=os.getenv("SENTINEL_WORKSPACE_ID", ""),
        azure_tenant_id=os.getenv("AZURE_TENANT_ID", ""),
        azure_client_id=os.getenv("AZURE_CLIENT_ID", ""),
        azure_client_secret=os.getenv("AZURE_CLIENT_SECRET", ""),
    )


def validate_env_vars() -> tuple[list[str], list[str]]:
    """Check all required env vars are present. Returns (passed, failed) lists.

    Shows ALL missing vars at once (not fail-fast) so the developer can fix
    them in one pass.
    """
    load_dotenv()
    passed: list[str] = []
    failed: list[str] = []
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var, "")
        if value:
            passed.append(var)
        else:
            failed.append(f"{var} ({description})")
    return passed, failed


def test_openai_connectivity(settings: Settings) -> tuple[bool, str]:
    """Test Azure OpenAI connectivity. Returns (success, message).

    Detects content filter errors specifically and returns an actionable message
    rather than a generic error.
    """
    try:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        response = client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=[{"role": "user", "content": "Hello, respond with OK."}],
            max_tokens=10,
        )
        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            return False, (
                "Content filter modification pending -- "
                "approval required before security queries work"
            )
        return True, "Azure OpenAI connected"

    except openai.BadRequestError as e:
        # Content filter on the input prompt
        if hasattr(e, "code") and e.code == "content_filter":
            return False, (
                "Content filter modification pending -- "
                "approval required before security queries work"
            )
        return False, f"Azure OpenAI error: {e.message}"

    except openai.AuthenticationError:
        return False, "Azure OpenAI authentication failed -- check API key"

    except openai.APIConnectionError:
        return False, "Azure OpenAI connection failed -- check endpoint URL"

    except openai.APIError as e:
        return False, f"Azure OpenAI error: {e.message}"


# Tell pytest this is not a test function
test_openai_connectivity.__test__ = False  # type: ignore[attr-defined]


def test_sentinel_connectivity(settings: Settings) -> tuple[bool, str]:
    """Test Sentinel workspace connectivity. Returns (success, message).

    Runs a minimal KQL query to verify workspace access.
    """
    try:
        credential = DefaultAzureCredential()
        client = LogsQueryClient(credential)
        response = client.query_workspace(
            workspace_id=settings.sentinel_workspace_id,
            query="SecurityIncident | take 1",
            timespan=timedelta(days=1),
        )
        if response.status == LogsQueryStatus.SUCCESS:
            return True, "Sentinel connected"
        elif response.status == LogsQueryStatus.PARTIAL:
            return True, "Sentinel connected (partial results)"
        else:
            return False, "Sentinel query returned no data"

    except Exception as e:
        error_msg = str(e)
        if "AuthenticationError" in error_msg or "401" in error_msg:
            return False, "Sentinel auth failed -- run 'az login' or check service principal"
        if "ResourceNotFound" in error_msg or "404" in error_msg:
            return False, "Sentinel workspace not found -- check SENTINEL_WORKSPACE_ID"
        return False, f"Sentinel error: {error_msg[:200]}"


# Tell pytest this is not a test function
test_sentinel_connectivity.__test__ = False  # type: ignore[attr-defined]


def validate_and_display() -> None:
    """Orchestrate two-layer validation and display results as a rich table.

    Layer 1: Check all required env vars are present.
    Layer 2: Test live connectivity to Azure services (only if Layer 1 passes).
    """
    console = Console()
    table = Table(title="Configuration Validation")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    # Layer 1: Environment variable validation
    passed, failed = validate_env_vars()

    for var in passed:
        table.add_row(f"Env: {var}", "[green]PASS[/green]", "Set")

    for var_desc in failed:
        table.add_row(f"Env: {var_desc.split(' (')[0]}", "[red]FAIL[/red]", f"Missing: {var_desc}")

    if failed:
        # Show all missing vars but skip connectivity checks
        console.print(table)
        console.print(
            f"\n[red]Validation failed:[/red] {len(failed)} required env var(s) missing. "
            "Connectivity checks skipped."
        )
        sys.exit(1)

    # Layer 2: Connectivity checks (only if all env vars pass)
    settings = load_settings()

    openai_ok, openai_msg = test_openai_connectivity(settings)
    table.add_row(
        "Azure OpenAI",
        "[green]PASS[/green]" if openai_ok else "[red]FAIL[/red]",
        openai_msg,
    )

    sentinel_ok, sentinel_msg = test_sentinel_connectivity(settings)
    table.add_row(
        "Sentinel",
        "[green]PASS[/green]" if sentinel_ok else "[red]FAIL[/red]",
        sentinel_msg,
    )

    console.print(table)

    if not openai_ok or not sentinel_ok:
        console.print("\n[red]Validation failed:[/red] One or more connectivity checks failed.")
        sys.exit(1)

    console.print("\n[green]All checks passed.[/green]")
    sys.exit(0)


if __name__ == "__main__":
    validate_and_display()
