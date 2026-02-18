---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [azure, openai, sentinel, provisioning, content-filter, env]

# Dependency graph
requires: []
provides:
  - Azure OpenAI resource with gpt-4o deployment (East US 2)
  - Custom content filter (High-only thresholds) applied to gpt-4o
  - Content filter modification request submitted (pending approval)
  - Sentinel workspace with Training Lab sample data
  - .env file with real Azure credentials
  - .env.example template with portal location comments
  - .gitignore covering secrets and Python artifacts
affects: [config, sentinel-client, openai-client]

# Tech tracking
tech-stack:
  added: [azure-openai, microsoft-sentinel, log-analytics]
  patterns: [default-azure-credential, content-filter-high-only]

key-files:
  created:
    - .env.example
    - .gitignore
    - .env
  modified: []

key-decisions:
  - "Named Azure OpenAI resource oai-sentinel-dev in East US 2"
  - "Content filter set to High-only on all 4 harm categories (most permissive without approval)"
  - "Content filter modification request submitted for full removal"
  - "Sentinel Training Lab used for sample data"
  - "Renamed sentinel-dev.env to .env for compatibility with python-dotenv defaults"

patterns-established:
  - "DefaultAzureCredential with az login for local development"
  - "Content filter High-only as fallback while modification request is pending"

requirements-completed: []

# Metrics
duration: manual (user-provisioned Azure resources)
completed: 2026-02-18
---

# Phase 1 Plan 01: Azure Resource Provisioning Summary

**Azure OpenAI resource with gpt-4o deployment, custom content filter, Sentinel workspace with Training Lab data, and .env populated with real credentials**

## Performance

- **Duration:** Manual provisioning (user action)
- **Started:** 2026-02-17
- **Completed:** 2026-02-18
- **Tasks:** 2 (1 automated, 1 human checkpoint)
- **Files created:** 3 (.env.example, .gitignore, .env)

## Accomplishments

- Azure OpenAI resource provisioned in East US 2 with gpt-4o Standard deployment
- Custom content filter "security-permissive" created with High-only thresholds on all 4 harm categories (violence, hate, sexual, self-harm) for both input and output
- Content filter modification request submitted via ncv.microsoft.com (approval pending, 1-3 business days)
- Sentinel workspace created with Microsoft Sentinel Training Lab installed (sample incidents, alerts, entities)
- .env populated with real AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, SENTINEL_WORKSPACE_ID values
- .env.example template documenting all variables with Azure Portal location comments
- .gitignore covering .env, Python bytecode, venv, ChromaDB data, IDE settings

## Task Commits

1. **Task 1: Create .env.example and .gitignore** - `cbcf442` (auto)
2. **Task 2: Azure resource provisioning and .env population** - Manual (user action, no commit)

## Connectivity Verification

All checks passed via `python -m src.config`:
- Env: AZURE_OPENAI_ENDPOINT — PASS
- Env: AZURE_OPENAI_API_KEY — PASS
- Env: SENTINEL_WORKSPACE_ID — PASS
- Azure OpenAI — PASS (gpt-4o responding)
- Sentinel — PASS (LogsQueryClient connected)

## Deviations from Plan

### Test Fix Required

**clean_env fixture needed load_dotenv patch**
- **Found during:** Post-provisioning test run
- **Issue:** Once .env exists on disk, `load_dotenv()` inside `validate_env_vars()` re-reads credentials, overriding the `clean_env` monkeypatch
- **Fix:** Added `monkeypatch.setattr("src.config.load_dotenv", lambda *a, **kw: None)` to `clean_env` fixture
- **Files modified:** tests/conftest.py
- **Verification:** All 11 tests pass

### Python Runtime Change

**Venv recreated with Python 3.14.2**
- Previous session used Python 3.12.10, but .venv is gitignored and didn't persist
- Python 3.12 no longer available on system; recreated with 3.14.2
- All dependencies install and tests pass on 3.14

## Issues Encountered

- Sentinel `InvalidTokenError` initially — user needed to `az login` with the correct account that has Log Analytics Reader role on the workspace
- 2 test failures from `clean_env` fixture not blocking `load_dotenv()` — fixed by patching

## Next Phase Readiness

- All Azure resources provisioned and verified
- Config module loads and validates all credentials
- Ready for Phase 2 (Sentinel Data Access) to build KQL queries against live data

---
*Phase: 01-foundation*
*Completed: 2026-02-18*
