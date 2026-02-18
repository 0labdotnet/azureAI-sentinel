# Phase 1: Foundation - Research

**Researched:** 2026-02-17
**Domain:** Azure resource provisioning, content filter modification, Python project scaffolding, config validation
**Confidence:** HIGH

## Summary

Phase 1 is an infrastructure-and-scaffolding phase with no formal requirement IDs. It creates the Azure resources (OpenAI + Sentinel workspace), submits the content filter modification request, and builds the Python project skeleton with a validated configuration module. The phase has two natural work units: (1) Azure provisioning + content filter submission, and (2) project scaffolding + `config.py` implementation with layered validation.

The content filter modification process is the critical-path item. All customers can already adjust content filter severity thresholds (High only, Medium+High, Low+Medium+High) without approval. Fully disabling or setting to "annotate only" requires submitting an application at `https://ncv.microsoft.com/uEfCgnITdR` -- approval is managed-customer-only and may take 1-3 business days. For this POC, the recommended first step is to create a custom content filter with the severity threshold set to "High only" (most permissive without approval), which will unblock most security content immediately. The full modification request should be submitted in parallel for cases where even High-threshold filtering blocks legitimate security queries.

The Python scaffolding is straightforward: `python-dotenv` for `.env` loading, a `Settings` dataclass to hold validated config, and a `__main__.py` entry point that runs layered validation (env vars first, then connectivity). Mock fixtures for Azure OpenAI responses enable development to continue during the content filter approval window.

**Primary recommendation:** Create the Azure OpenAI resource in East US 2 (best gpt-4o availability), create a custom content filter with "High only" thresholds for all four harm categories and associate it with the gpt-4o deployment, submit the full modification request form, then scaffold the Python project with `config.py` implementing two-layer validation (env vars, then connectivity) with content-filter-specific error detection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `python -m src.config` performs layered validation: first checks all env vars are present, then attempts live connectivity only if env vars pass
- Env vars are grouped by phase: Phase 1 vars (Azure OpenAI endpoint, Sentinel workspace ID, auth) are required; later-phase vars (ChromaDB path, embedding config) are optional and noted as "not yet needed"
- On success, displays a summary table showing all checked items with pass/fail status (env vars loaded, OpenAI connected, Sentinel connected)
- On failure, shows all missing/invalid env vars at once (not fail-fast), but skips connectivity checks if env vars are incomplete
- If Azure OpenAI returns a content filter error during connectivity check, show a specific message: "Content filter modification pending -- approval required before security queries work" (not a generic connection error)
- Create mock Azure OpenAI responses so development can continue during the 1-3 business day content filter approval window
- Mocks should cover: chat completion responses, tool call responses, and content filter rejection responses
- Include a documented `.env.example` with every variable, grouped by service (Azure OpenAI, Sentinel, Auth), with inline comments explaining each variable and where to find the values in Azure portal
- Audience is a small team (2-3 developers) -- setup docs should be clear but not enterprise-grade
- `python -m src.config` is the single verification command -- no separate verify script needed
- Target Python 3.12 explicitly (document in README/pyproject)
- Use `requirements.txt` with pinned versions for dependency management
- Neither Azure OpenAI nor Sentinel workspace exists yet -- both must be provisioned as part of Phase 1
- Content filter modification request process needs to be researched (user hasn't gone through it before)
- Plan 01-01 should include step-by-step provisioning guidance and content filter submission instructions

### Claude's Discretion
- Exact table formatting for config validation output
- Mock response fixture design and storage location
- `.env.example` grouping order and comment style
- Error message wording for non-content-filter failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core (Phase 1 Only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-dotenv | >=1.0.0 | Load `.env` file into `os.environ` | Simple, zero-dependency, stable. 1.2.1 is latest. |
| azure-identity | >=1.25.0 | `DefaultAzureCredential` for all Azure auth | Single credential chain for both local dev (`az login`) and service principal. |
| azure-monitor-query | >=2.0.0 | Connectivity test via `LogsQueryClient` | Required for Sentinel KQL queries. Only maintained SDK for this purpose. |
| openai | >=2.21.0 | Connectivity test via `AzureOpenAI` client | v2.x is the active branch. Used for chat completions test. |
| rich | >=14.0.0 | Config validation summary table output | Used for formatted terminal output throughout the project. |

### Development

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=9.0.0 | Test framework | Unit tests for config validation, mock fixtures |
| ruff | >=0.15.0 | Linting + formatting | Replace flake8+black+isort in one tool |

### Not Needed in Phase 1

| Library | Why Deferred |
|---------|-------------|
| chromadb | Phase 4 (Knowledge Base) |
| tiktoken | Phase 3 (AI Orchestration) |
| requests | Phase 2 (Sentinel REST API calls) |
| pytest-cov | Phase 6 (Testing) |

**Installation (Phase 1 requirements.txt):**
```
# Azure SDKs
azure-identity>=1.25.0
azure-monitor-query>=2.0.0

# Azure OpenAI
openai>=2.21.0

# Utilities
python-dotenv>=1.0.0
rich>=14.0.0
```

**Development (requirements-dev.txt):**
```
pytest>=9.0.0
ruff>=0.15.0
```

## Architecture Patterns

### Recommended Project Structure (Phase 1 Deliverables)

```
azureAI-sentinel/
+-- src/
|   +-- __init__.py           # Package init (empty)
|   +-- __main__.py           # Enables `python -m src.config` execution
|   +-- config.py             # Settings dataclass, env validation, connectivity checks
+-- tests/
|   +-- __init__.py           # Package init (empty)
|   +-- conftest.py           # Shared pytest fixtures
|   +-- test_config.py        # Config validation unit tests
|   +-- fixtures/             # Mock Azure OpenAI response JSON files
|       +-- chat_completion.json
|       +-- tool_call_response.json
|       +-- content_filter_error.json
+-- .env.example              # Template with all variables, grouped by service
+-- .gitignore                # .env, __pycache__, .venv/, data/chroma_db/
+-- requirements.txt          # Pinned production dependencies
+-- requirements-dev.txt      # Pinned development dependencies
+-- pyproject.toml            # Python 3.12, ruff, pytest config
+-- README.md                 # Setup instructions for team
```

### Pattern 1: Layered Configuration Validation

**What:** Load env vars from `.env`, validate presence of all required vars (layer 1), then test live connectivity to Azure services (layer 2). Skip layer 2 if layer 1 fails.

**When to use:** On `python -m src.config` -- the single verification command.

**Example:**

```python
import os
import sys
from dataclasses import dataclass, field
from dotenv import load_dotenv
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


# Phase 1 required vars -- later phases add to this
REQUIRED_VARS = {
    "AZURE_OPENAI_ENDPOINT": "Azure OpenAI endpoint URL",
    "AZURE_OPENAI_API_KEY": "Azure OpenAI API key",
    "SENTINEL_WORKSPACE_ID": "Log Analytics workspace GUID",
}

# Phase 2+ optional vars -- noted as "not yet needed"
OPTIONAL_VARS = {
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
    """Check all required env vars are present. Returns (passed, failed) lists."""
    passed = []
    failed = []
    for var, description in REQUIRED_VARS.items():
        value = os.getenv(var, "")
        if value:
            passed.append(var)
        else:
            failed.append(f"{var} ({description})")
    return passed, failed
```

### Pattern 2: Content Filter Error Detection

**What:** When testing Azure OpenAI connectivity, specifically detect content filter errors and surface a targeted, actionable message rather than a generic error.

**When to use:** During the connectivity check in `python -m src.config`.

**Critical detail:** The openai v2.x SDK raises `openai.BadRequestError` (HTTP 400) when a prompt triggers the content filter. The error object has a `code` attribute of `"content_filter"`. On the response side, `finish_reason == "content_filter"` indicates the output was filtered.

**Example:**

```python
import openai
from openai import AzureOpenAI


def test_openai_connectivity(settings: Settings) -> tuple[bool, str]:
    """Test Azure OpenAI connectivity. Returns (success, message)."""
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
```

### Pattern 3: Sentinel Connectivity Test

**What:** Execute a minimal KQL query to verify Sentinel workspace access.

**Example:**

```python
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from datetime import timedelta


def test_sentinel_connectivity(settings: Settings) -> tuple[bool, str]:
    """Test Sentinel workspace connectivity. Returns (success, message)."""
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
```

### Anti-Patterns to Avoid

- **Fail-fast on first missing env var:** User decision requires showing ALL missing vars at once so the developer can fix them in one pass, not one at a time.
- **Generic error messages for content filter:** User explicitly decided that content filter errors must be recognizable and actionable, not buried in Azure SDK exceptions.
- **Creating a separate verify script:** User decided `python -m src.config` is the single verification command.
- **Installing all dependencies in Phase 1:** Only install what Phase 1 needs. ChromaDB, tiktoken, and requests are not used until later phases.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Azure credential management | Custom token acquisition | `DefaultAzureCredential` from azure-identity | Handles `az login`, service principal, managed identity automatically with built-in token caching |
| Environment variable loading | Custom `.env` parser | `python-dotenv` `load_dotenv()` | Handles comments, quoting, multiline values, encoding edge cases |
| Terminal formatting for tables | Custom ANSI codes | `rich.table.Table` | Cross-platform, handles column width, Unicode, color consistently |
| Content filter detection | String matching on error messages | Check `openai.BadRequestError.code == "content_filter"` and `finish_reason == "content_filter"` | SDK provides structured error codes; string matching is brittle |

## Common Pitfalls

### Pitfall 1: Content Filter Blocking Benign Test Prompts

**What goes wrong:** Even the "Hello, respond with OK" test prompt can sometimes be flagged if the content filter is misconfigured or overly aggressive. More importantly, security-related test prompts ("describe a brute force attack investigation") will be blocked by the default Medium+High filter.
**Why it happens:** The default content filter blocks at Medium severity for all four harm categories (violence, hate, sexual, self-harm). Security operations content frequently intersects with the "violence" category at Medium severity.
**How to avoid:**
1. Create a custom content filter in Azure AI Foundry with thresholds set to "High only" for all categories (the most permissive setting available without approval).
2. Associate this custom filter with the gpt-4o deployment.
3. Submit the full modification request form for "annotate only" or "no filters" access.
4. Use a benign test prompt for the connectivity check (not security content).
**Warning signs:** `finish_reason: "content_filter"` on responses, HTTP 400 with `code: "content_filter"`.

### Pitfall 2: Azure OpenAI Resource Region Choice

**What goes wrong:** gpt-4o is not available in all Azure regions. Creating the resource in a region without gpt-4o model availability means you cannot deploy the model.
**Why it happens:** Azure OpenAI model availability varies by region and changes over time. Not all regions support all deployment types.
**How to avoid:** Create the Azure OpenAI resource in **East US 2** (recommended) or **Sweden Central**. Both have strong gpt-4o Standard deployment availability. Verify in the Azure AI Foundry portal model catalog before provisioning.
**Warning signs:** Model deployment creation fails with "model not available in this region" error.

### Pitfall 3: Sentinel Workspace Without Sample Data

**What goes wrong:** A brand-new Sentinel workspace has no incidents or alerts. The `SecurityIncident | take 1` connectivity test returns zero rows, which is technically a success but misleading -- later phases depend on actual data existing.
**Why it happens:** Sentinel only generates incidents when analytics rules fire on ingested data. A fresh workspace has no data connectors and no rules.
**How to avoid:** After enabling Sentinel, deploy the **Microsoft Sentinel Training Lab** solution from the Content Hub. This ingests sample security data (incidents, alerts, entities) that closely simulates real-world scenarios. The training lab provides enough data for all POC development and testing.
**Warning signs:** `SecurityIncident | count` returns 0.

### Pitfall 4: Python Version Mismatch

**What goes wrong:** The system has Python 3.14.3 installed. ChromaDB 1.5.0 (needed in Phase 4) may not have prebuilt wheels for Python 3.14, which would require compiling native C extensions and installing a C compiler.
**Why it happens:** Python 3.14 is very new; many packages lag behind on wheel availability for new Python versions.
**How to avoid:** Create the project venv explicitly with Python 3.12: `py -3.12 -m venv .venv` (Windows). Document Python 3.12 as the target in both `pyproject.toml` (`requires-python = ">=3.11,<3.14"`) and the README. Ensure Python 3.12 is installed on the system.
**Warning signs:** `pip install chromadb` fails with compilation errors in Phase 4.

### Pitfall 5: DefaultAzureCredential Picks Wrong Credential

**What goes wrong:** On a developer machine with both Azure CLI logged in AND service principal env vars set, `DefaultAzureCredential` tries credentials in a fixed order (EnvironmentCredential first). If the env vars point to a different tenant than `az login`, requests fail with confusing auth errors.
**Why it happens:** `DefaultAzureCredential` tries EnvironmentCredential before AzureCliCredential. If `AZURE_CLIENT_ID` and `AZURE_CLIENT_SECRET` are set (even stale values), it uses those first.
**How to avoid:** For local development, do NOT set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` in `.env`. Use `az login` only. Service principal vars are only for CI/deployment. Document this clearly in `.env.example`.
**Warning signs:** Auth errors that mention "tenant not found" or "invalid client secret" when `az login` works fine.

## Code Examples

### Mock Azure OpenAI Response Fixtures

Store mock responses as JSON files in `tests/fixtures/`. This enables development to continue during the content filter approval window.

**Recommendation:** Store fixtures in `tests/fixtures/` directory as JSON files. Load them with `pathlib.Path` + `json.load` in conftest.py fixtures.

**tests/fixtures/chat_completion.json:**
```json
{
    "id": "chatcmpl-mock-001",
    "object": "chat.completion",
    "created": 1708000000,
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Based on the security incident data, here are the 3 high-severity incidents from the last 24 hours..."
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 150,
        "completion_tokens": 200,
        "total_tokens": 350
    }
}
```

**tests/fixtures/tool_call_response.json:**
```json
{
    "id": "chatcmpl-mock-002",
    "object": "chat.completion",
    "created": 1708000000,
    "model": "gpt-4o",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": null,
                "tool_calls": [
                    {
                        "id": "call_mock_001",
                        "type": "function",
                        "function": {
                            "name": "query_sentinel_incidents",
                            "arguments": "{\"severity\": \"High\", \"time_range_hours\": 24}"
                        }
                    }
                ]
            },
            "finish_reason": "tool_calls"
        }
    ],
    "usage": {
        "prompt_tokens": 250,
        "completion_tokens": 50,
        "total_tokens": 300
    }
}
```

**tests/fixtures/content_filter_error.json:**
```json
{
    "error": {
        "message": "The response was filtered due to the prompt triggering Azure OpenAI's content management policy. Please modify your prompt and retry.",
        "type": null,
        "param": "prompt",
        "code": "content_filter",
        "status": 400,
        "innererror": {
            "code": "ResponsibleAIPolicyViolation",
            "content_filter_result": {
                "hate": {"filtered": false, "severity": "safe"},
                "self_harm": {"filtered": false, "severity": "safe"},
                "sexual": {"filtered": false, "severity": "safe"},
                "violence": {"filtered": true, "severity": "medium"}
            }
        }
    }
}
```

### .env.example Template

```bash
# ============================================================
# Azure OpenAI Configuration
# ============================================================
# Find in: Azure Portal > Resource Group > OpenAI resource > Keys and Endpoint
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here

# Model deployment names (must match deployment names in Azure AI Foundry)
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
# AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large  # Phase 4

# API version for Azure OpenAI
AZURE_OPENAI_API_VERSION=2024-10-21

# ============================================================
# Microsoft Sentinel / Log Analytics
# ============================================================
# Find in: Azure Portal > Log Analytics workspace > Overview > Workspace ID
SENTINEL_WORKSPACE_ID=00000000-0000-0000-0000-000000000000

# Only needed for Sentinel REST API (Phase 2+)
# SENTINEL_SUBSCRIPTION_ID=your-subscription-id
# SENTINEL_RESOURCE_GROUP=your-resource-group
# SENTINEL_WORKSPACE_NAME=your-workspace-name

# ============================================================
# Azure Authentication
# ============================================================
# Option A: Use 'az login' for local development (recommended)
#   No env vars needed -- DefaultAzureCredential auto-detects.
#
# Option B: Service principal (CI/deployment only)
#   Find in: Azure Portal > Entra ID > App Registrations > your app
# AZURE_TENANT_ID=your-tenant-id
# AZURE_CLIENT_ID=your-client-id
# AZURE_CLIENT_SECRET=your-client-secret
```

### pyproject.toml Template

```toml
[project]
name = "sentinel-rag-chatbot"
version = "0.1.0"
requires-python = ">=3.11,<3.14"
description = "POC chatbot for querying Microsoft Sentinel via Azure OpenAI"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests requiring live Azure resources (deselect with '-m \"not integration\"')",
]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]
```

## Azure Resource Provisioning Guide

### Step 1: Create Azure OpenAI Resource

**Via Azure Portal:**
1. Sign in to [Azure Portal](https://portal.azure.com)
2. Select "Create a resource" and search for "Azure OpenAI"
3. Configure:
   - **Subscription:** Your Azure subscription
   - **Resource group:** Create new (e.g., `rg-sentinel-chatbot`)
   - **Region:** **East US 2** (recommended for gpt-4o availability)
   - **Name:** e.g., `oai-sentinel-chatbot`
   - **Pricing Tier:** Standard S0
4. Network: "All networks" is fine for POC
5. Review + Create

**Via Azure CLI:**
```bash
az group create --name rg-sentinel-chatbot --location eastus2

az cognitiveservices account create \
    --name oai-sentinel-chatbot \
    --resource-group rg-sentinel-chatbot \
    --location eastus2 \
    --kind OpenAI \
    --sku s0 \
    --custom-domain oai-sentinel-chatbot
```

### Step 2: Deploy gpt-4o Model

**Via Azure AI Foundry (ai.azure.com):**
1. Sign in to [Azure AI Foundry](https://ai.azure.com)
2. Under "Keep building with Foundry" select "View all resources"
3. Find and select your OpenAI resource
4. Select Deployments > + Deploy model > Deploy base model
5. Select **gpt-4o** > Confirm
6. Configure:
   - **Deployment name:** `gpt-4o`
   - **Deployment type:** Standard
   - **Model version:** 2024-11-20
   - **TPM rate limit:** Start with default (adjust later if needed)
7. Deploy

**Via Azure CLI:**
```bash
az cognitiveservices account deployment create \
    --name oai-sentinel-chatbot \
    --resource-group rg-sentinel-chatbot \
    --deployment-name gpt-4o \
    --model-name gpt-4o \
    --model-version "2024-11-20" \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"
```

### Step 3: Get Endpoint and API Key

**Via Azure CLI:**
```bash
# Get endpoint
az cognitiveservices account show \
    --name oai-sentinel-chatbot \
    --resource-group rg-sentinel-chatbot \
    | jq -r .properties.endpoint

# Get API key
az cognitiveservices account keys list \
    --name oai-sentinel-chatbot \
    --resource-group rg-sentinel-chatbot \
    | jq -r .key1
```

**Via Azure Portal:**
Navigate to your OpenAI resource > "Keys and Endpoint" in the left menu.

### Step 4: Create and Apply Custom Content Filter

This is the most important step for this security-focused POC. The default content filter blocks at Medium severity, which will interfere with security content.

**Create a custom filter (no approval needed):**
1. Sign in to [Azure AI Foundry](https://ai.azure.com)
2. Navigate to your project
3. Select **Guardrails + controls** > **Content filters** tab
4. Select **+ Create content filter**
5. Name it: `security-permissive`
6. **Input filters:** Set all four harm categories (violence, hate, sexual, self-harm) to **High only** (the slider should be set so only High severity is blocked)
7. **Output filters:** Same -- set all four to **High only**
8. Leave Prompt Shields enabled (on)
9. On the Connection page, associate with the gpt-4o deployment
10. Review + Create

**Submit Modified Content Filtering Request (for full control):**
1. Navigate to: [https://ncv.microsoft.com/uEfCgnITdR](https://ncv.microsoft.com/uEfCgnITdR)
2. Fill out the "Limited Access Review: Modified Content Filters" form
3. Describe the use case: "Security operations chatbot querying Microsoft Sentinel SIEM data. Requires processing security incident descriptions, MITRE ATT&CK technique names, malware descriptions, and phishing content for legitimate SOC analyst workflows."
4. Submit and wait for approval (typically 1-3 business days)
5. Once approved, update the custom filter to "Annotate only" or "No filters" for the violence and hate categories

**Important notes:**
- All customers can adjust severity thresholds (High/Medium/Low) without approval
- Only "managed customers" who are approved can set to "No filters" or "Annotate only"
- The note in the docs states: "At this time, it is not possible to become a managed customer" -- this means the full modification request may be denied
- The "High only" threshold should unblock most security content for the POC
- If the full modification is not approved, the "High only" custom filter is the fallback

### Step 5: Create Sentinel Workspace

**Via Azure Portal:**
1. Search for "Microsoft Sentinel" in Azure Portal
2. Select Create
3. Select "Create a new workspace"
4. Configure:
   - **Subscription:** Same subscription
   - **Resource group:** `rg-sentinel-chatbot` (same as OpenAI)
   - **Name:** e.g., `law-sentinel-chatbot`
   - **Region:** Same region as OpenAI resource for lowest latency
5. Review + Create
6. After workspace is created, select it and click "Add" to enable Sentinel

**Required permissions:**
- **Contributor** on the subscription to enable Sentinel
- **Microsoft Sentinel Contributor** or **Reader** on the resource group

### Step 6: Deploy Sentinel Training Lab (Sample Data)

1. In Microsoft Sentinel, go to **Content Hub**
2. Search for "Microsoft Sentinel Training Lab"
3. Select **Install**
4. Follow the deployment wizard
5. The training lab ingests sample incidents, alerts, and entities via a PowerShell script using the Log Analytics Data Collector API
6. Wait 5-10 minutes for data to appear
7. Verify: Run `SecurityIncident | count` in the Logs blade -- should return > 0

### Step 7: Configure RBAC for the Service Principal (if using)

If using a service principal (not `az login`):
```bash
# Get the workspace resource ID
WORKSPACE_ID=$(az monitor log-analytics workspace show \
    --resource-group rg-sentinel-chatbot \
    --workspace-name law-sentinel-chatbot \
    --query id -o tsv)

# Assign roles
az role assignment create \
    --assignee <client-id> \
    --role "Microsoft Sentinel Reader" \
    --scope $WORKSPACE_ID

az role assignment create \
    --assignee <client-id> \
    --role "Log Analytics Reader" \
    --scope $WORKSPACE_ID

az role assignment create \
    --assignee <client-id> \
    --role "Cognitive Services OpenAI User" \
    --scope /subscriptions/<sub-id>/resourceGroups/rg-sentinel-chatbot/providers/Microsoft.CognitiveServices/accounts/oai-sentinel-chatbot
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `openai` v1.x `AzureOpenAI` | `openai` v2.x `AzureOpenAI` (with v1 endpoint support) | Sep 2025 | v2.x is the active branch; v1.x is maintenance-only |
| `api_version` required | `/openai/v1/` endpoint removes need for `api_version` | Aug 2025 | Only for resources created after Aug 2025; older resources still need `api_version` |
| `functions`/`function_call` API | `tools`/`tool_choice` API | 2024 | `functions` is deprecated; use `tools` only |
| Content filter: no configurability | All customers can adjust severity thresholds | 2025 | Allows "High only" without approval; "No filters" needs approval form |
| Azure AI Studio | Azure AI Foundry (rebranded) | Late 2025 | Same portal at ai.azure.com, new name and UI |
| `azure-mgmt-securityinsight` | `azure-monitor-query` v2.0.0 | Jul 2025 | Old package abandoned since Jul 2022; new package is actively maintained |

**Deprecated/outdated:**
- `azure-mgmt-securityinsight` v1.0.0: Last released July 2022, effectively abandoned. Do not use.
- `functions`/`function_call` parameters in OpenAI API: Deprecated in favor of `tools`/`tool_choice`.
- `openai.error` module: Removed in v2.x. Import exceptions directly from `openai` (e.g., `openai.BadRequestError`).
- Azure AI Studio: Rebranded to Azure AI Foundry. All documentation references "Microsoft Foundry" now.

## Open Questions

1. **Content filter modification approval timeline**
   - What we know: The form is at `https://ncv.microsoft.com/uEfCgnITdR`. The docs state "At this time, it is not possible to become a managed customer" which may mean the request is denied.
   - What's unclear: Whether the "High only" custom filter is sufficient for all security content the POC will process, or whether some legitimate security queries will still be blocked.
   - Recommendation: Set up "High only" filter immediately (no approval needed). Submit the modification request in parallel. Track any content-filter-blocked queries during Phase 2 development to build an evidence case. The mock fixtures allow development to continue regardless.

2. **Azure OpenAI endpoint format (legacy vs. v1)**
   - What we know: Resources created after August 2025 support the `/openai/v1/` endpoint that does not require `api_version`. Older resources use the legacy format.
   - What's unclear: Which format the newly-created resource will use.
   - Recommendation: Since this is a brand-new resource, it should use the v1 endpoint. However, keep `api_version` in the config as a safety net -- the `AzureOpenAI` client accepts it regardless.

3. **Sentinel Training Lab data retention**
   - What we know: Training Lab ingests sample data via the Log Analytics Data Collector API. Default retention is 30 days.
   - What's unclear: Whether the training lab data needs to be re-ingested if the workspace retention period is reached during development.
   - Recommendation: Increase Log Analytics retention to 90 days immediately after workspace creation (`az monitor log-analytics workspace update --retention-in-days 90`).

## Sources

### Primary (HIGH confidence)
- [Configure content filters - Azure OpenAI](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/content-filters) -- updated 2025-12-03, verified content filter creation process, severity thresholds, managed customer requirements
- [Content Filter Configurability](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/content-filter-configurability) -- verified approval form URL (`https://ncv.microsoft.com/uEfCgnITdR`), configurability levels, managed customer note
- [Content filtering for Microsoft Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/content-filter) -- updated 2026-02-04, verified content filtering API scenarios (finish_reason, HTTP 400, error codes)
- [Create and deploy Azure OpenAI resource](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/create-resource) -- updated 2025-11-26, verified Azure Portal, CLI, and PowerShell provisioning steps
- [Onboard to Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/quickstart-onboard) -- updated 2025-09-04, verified workspace creation and Sentinel enablement steps
- [Microsoft Sentinel Training Lab](https://techcommunity.microsoft.com/blog/microsoftsentinelblog/learning-with-the-microsoft-sentinel-training-lab/2953403) -- verified training lab provides sample incidents/alerts/entities
- Project INITIAL-RESEARCH.md, CLAUDE.md, STACK.md, ARCHITECTURE.md, PITFALLS.md -- pre-existing project research, verified design decisions

### Secondary (MEDIUM confidence)
- [openai-python GitHub](https://github.com/openai/openai-python) -- verified exception class hierarchy (BadRequestError, AuthenticationError, etc.) for v2.x
- [OpenAI Error Codes](https://platform.openai.com/docs/guides/error-codes) -- verified status code to exception class mapping
- [python-dotenv GitHub](https://github.com/theskumar/python-dotenv) -- verified load_dotenv() behavior and API

### Tertiary (LOW confidence)
- Content filter modification approval timeline ("1-3 business days") -- sourced from community posts and project PITFALLS.md; not officially documented by Microsoft
- "At this time, it is not possible to become a managed customer" -- exact meaning is unclear; may mean full filter removal is restricted, not that the form is useless

## Metadata

**Confidence breakdown:**
- Azure provisioning steps: HIGH -- official Microsoft docs, CLI commands verified
- Content filter process: HIGH -- official docs with form URL, but LOW confidence on approval timeline/outcome
- Python config patterns: HIGH -- standard python-dotenv usage, well-understood
- Mock fixture design: HIGH -- standard pytest patterns
- Content filter error detection: HIGH -- verified against official API response schemas
- Sentinel Training Lab: MEDIUM -- verified it exists and provides sample data, but exact data coverage not confirmed

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (30 days -- Azure portal UI may change but CLI commands and APIs are stable)
