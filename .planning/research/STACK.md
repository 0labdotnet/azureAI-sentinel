# Technology Stack

**Project:** Azure Sentinel RAG Chatbot POC
**Researched:** 2026-02-16
**Overall confidence:** HIGH

---

## Version Verification Method

All package versions verified against PyPI on 2026-02-16 using `pip install <pkg>==999` to enumerate available versions. The INITIAL-RESEARCH.md versions were cross-checked and confirmed accurate for all core dependencies.

---

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | >=3.11, <3.14 | Runtime | 3.11 is the sweet spot: stable, performant (10-60% faster than 3.10 per CPython benchmarks), well-supported by all Azure SDKs. Avoid 3.14 (too new, ChromaDB and other native deps may not have wheels). The project specifies 3.10+ but 3.11 should be the minimum for new projects in 2026. | HIGH |

**Note on Python 3.14:** The system has Python 3.14.3 installed. ChromaDB 1.5.0 may not have prebuilt wheels for 3.14 yet, which would require compiling native extensions. Recommend using 3.11 or 3.12 in the project venv to avoid build issues.

### Azure OpenAI

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| openai | >=2.21.0 | Azure OpenAI chat completions + embeddings | v2.x is the current major version (released Sep 2025). Includes `AzureOpenAI` client, native `tools` parameter support, structured outputs, and streaming. The v1.x branch is in maintenance. | HIGH |

### Azure Authentication + Data Access

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| azure-identity | >=1.25.0 | `DefaultAzureCredential` for all Azure auth | Supports `az login` for dev and service principal for deployment. Single credential chain covers all Azure services. 1.25.2 is latest stable. | HIGH |
| azure-monitor-query | >=2.0.0 | KQL queries via `LogsQueryClient` | The only maintained SDK for querying Log Analytics / Sentinel data via KQL. v2.0.0 is the current major release. | HIGH |

### Vector Store

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| chromadb | >=1.5.0 | Local persistent vector store | Zero-config setup, built-in metadata filtering (severity, status, timestamp), built-in persistence. v1.x is a major rewrite from v0.x with improved APIs. Perfect for POC; migrate to Azure AI Search for production. | HIGH |

### CLI and UX

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| rich | >=14.0.0 | Terminal formatting (tables, markdown, colors) | De facto standard for beautiful CLI output in Python. Supports tables for incident lists, color-coded severity levels, markdown rendering for LLM responses, spinners for loading indicators. v14 is current. | HIGH |

### Utilities

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| tiktoken | >=0.12.0 | Token counting for context window management | OpenAI's official tokenizer. Required to count tokens before sending to LLM and truncate conversation history when approaching the 128K context limit. 0.12.0 is latest. | HIGH |
| python-dotenv | >=1.0.0 | Load `.env` file into environment | Simple, stable, zero-dependency. 1.2.1 is latest. | HIGH |
| requests | >=2.32.0 | HTTP client for Sentinel REST API direct calls | Used for Sentinel management API endpoints (incidents, alerts) where `azure-monitor-query` (KQL-only) is insufficient. 2.32.5 is latest stable. | HIGH |

### Development and Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| pytest | >=9.0.0 | Test framework | Industry standard. v9.0 is the latest major release. Supports fixtures, parametrize, markers -- everything needed for unit and integration tests. | HIGH |
| pytest-cov | >=7.0.0 | Coverage reporting | Generates coverage reports. Useful for POC demos to show test quality. 7.0.0 is latest. | HIGH |
| pytest-asyncio | >=1.0.0 | Async test support | Needed if any async patterns are used (e.g., async Azure SDK calls). v1.x is current stable. Only install if using async code. | MEDIUM |
| ruff | >=0.15.0 | Linting + formatting | Replaces flake8 + black + isort in a single tool. 10-100x faster (written in Rust). 0.15.1 is latest. The standard choice for new Python projects in 2025/2026. | HIGH |
| mypy | >=1.19.0 | Static type checking | Catches type errors before runtime. Valuable for Azure SDK code where types are well-defined. 1.19.1 is latest. Optional for POC but recommended. | MEDIUM |

---

## Validation of Existing Design Decisions

The following decisions from CLAUDE.md / INITIAL-RESEARCH.md have been validated:

### CONFIRMED: No LangChain

**Verdict: Correct decision.**

The INITIAL-RESEARCH.md section 9.4 lists LangChain packages (`langchain>=1.2.0`, `langchain-openai>=1.1.0`, etc.) as optional. The CLAUDE.md correctly overrides this to "No LangChain." For a 12-day POC:

- LangChain adds ~15 transitive dependencies and significant abstraction overhead
- Direct `openai` SDK function calling is straightforward (define tools, handle tool_calls, send results back)
- LangChain's abstractions make debugging opaque -- bad for a POC meant to demonstrate understanding
- The agentic loop (chat -> tool calls -> execute -> send results -> final response) is ~50 lines of code without LangChain

### CONFIRMED: openai v2.x, not v1.x

**Verdict: Correct.** v2.x (latest: 2.21.0) is the active development branch. v1.x (latest: 1.109.1) is maintenance-only. The `tools` parameter (not deprecated `functions`) is native to v2.x.

### CONFIRMED: `azure-monitor-query` for KQL, not `azure-mgmt-securityinsight`

**Verdict: Correct.** `azure-mgmt-securityinsight` v1.0.0 was last released July 2022 and is effectively abandoned. `azure-monitor-query` v2.0.0 is actively maintained and provides `LogsQueryClient` which can query all Sentinel tables via KQL.

### CONFIRMED: `tools` parameter, not `functions`

**Verdict: Correct.** The `functions`/`function_call` parameters are deprecated in the OpenAI API. Use `tools`/`tool_choice`.

### CONFIRMED: text-embedding-3-large at 1024 dimensions

**Verdict: Correct.** Truncating from 3072 to 1024 dimensions gives ~1-2% accuracy loss on retrieval benchmarks but 3x storage savings. For a POC with hundreds (not millions) of documents, the storage savings are negligible, but 1024D is still the right choice because it matches ChromaDB's default HNSW performance characteristics better.

### CONFIRMED: Pre-defined KQL templates only

**Verdict: Correct.** LLMs generate syntactically broken KQL for anything beyond basic queries. Parameterized templates are safer and auditable. The LLM picks which template to call; it does not write KQL.

---

## Discrepancy Found in INITIAL-RESEARCH.md

**Section 9.3** states "Minimum Python version: 3.10+ (required by LangChain)." Since LangChain is not being used, this rationale is wrong. The actual minimum should be Python 3.10+ because `azure-monitor-query` v2.0.0 requires it (and `match` statements, `|` union types, etc. are 3.10+ features). Recommend 3.11+ in practice for performance.

**Section 9.4** lists `azure-search-documents>=11.6.0` as a core dependency. This is not needed for the POC -- it is for Azure AI Search, which is the production vector store, not ChromaDB. Remove from requirements.txt.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| LLM SDK | openai v2.x | LangChain / Semantic Kernel | Unnecessary abstraction for POC; function calling is native in openai SDK |
| KQL Access | azure-monitor-query | azure-mgmt-securityinsight | Stale package (2022), limited to management operations, no KQL |
| Vector Store | ChromaDB | FAISS | FAISS lacks built-in metadata filtering and persistence; ChromaDB is zero-config |
| Vector Store | ChromaDB | Azure AI Search | Requires Azure resource provisioning; overkill for POC with <1000 documents |
| Linter | ruff | flake8 + black + isort | ruff replaces all three in one tool, 100x faster |
| Type Checker | mypy | pyright / pytype | mypy is most mature; best Azure SDK stub coverage |
| Formatting | ruff format | black | ruff includes a black-compatible formatter; no need for separate tool |
| Test Framework | pytest | unittest | pytest is more ergonomic (fixtures, parametrize, better assertions) |
| HTTP Client | requests | httpx | requests is simpler for sync code; httpx preferred only if going async |
| Config | python-dotenv | pydantic-settings | python-dotenv is lighter; pydantic-settings adds validation but is overkill for POC |

---

## Dependencies NOT Needed

These are listed in INITIAL-RESEARCH.md but should NOT be in the POC's requirements.txt:

| Package | Why Not |
|---------|---------|
| `azure-search-documents` | Production vector store; POC uses ChromaDB |
| `langchain` | Explicitly excluded per architecture decision |
| `langchain-openai` | See above |
| `langchain-community` | See above |
| `langchain-chroma` | See above |
| `msgraph-sdk` | Graph API is optional enrichment; POC uses KQL + Sentinel REST API directly |

---

## Installation

### requirements.txt (production dependencies)

```
# Azure SDKs
azure-identity>=1.25.0
azure-monitor-query>=2.0.0

# Azure OpenAI
openai>=2.21.0

# Local vector store
chromadb>=1.5.0

# Utilities
tiktoken>=0.12.0
python-dotenv>=1.0.0
requests>=2.32.0
rich>=14.0.0
```

### requirements-dev.txt (development dependencies)

```
# Testing
pytest>=9.0.0
pytest-cov>=7.0.0

# Linting and formatting
ruff>=0.15.0

# Type checking (optional but recommended)
mypy>=1.19.0
```

### Setup commands

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Configuration: pyproject.toml

Consolidate tool config in `pyproject.toml` rather than scattered config files:

```toml
[project]
name = "sentinel-rag-chatbot"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests requiring live Azure resources",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = false
warn_return_any = true
warn_unused_configs = true
```

---

## Sources

All versions verified directly against PyPI on 2026-02-16:

- openai 2.21.0: [PyPI](https://pypi.org/project/openai/) -- HIGH confidence
- azure-monitor-query 2.0.0: [PyPI](https://pypi.org/project/azure-monitor-query/) -- HIGH confidence
- azure-identity 1.25.2: [PyPI](https://pypi.org/project/azure-identity/) -- HIGH confidence
- chromadb 1.5.0: [PyPI](https://pypi.org/project/chromadb/) -- HIGH confidence
- tiktoken 0.12.0: [PyPI](https://pypi.org/project/tiktoken/) -- HIGH confidence
- rich 14.3.2: [PyPI](https://pypi.org/project/rich/) -- HIGH confidence
- python-dotenv 1.2.1: [PyPI](https://pypi.org/project/python-dotenv/) -- HIGH confidence
- requests 2.32.5: [PyPI](https://pypi.org/project/requests/) -- HIGH confidence
- pytest 9.0.2: [PyPI](https://pypi.org/project/pytest/) -- HIGH confidence
- pytest-cov 7.0.0: [PyPI](https://pypi.org/project/pytest-cov/) -- HIGH confidence
- ruff 0.15.1: [PyPI](https://pypi.org/project/ruff/) -- HIGH confidence
- mypy 1.19.1: [PyPI](https://pypi.org/project/mypy/) -- HIGH confidence

INITIAL-RESEARCH.md design decisions validated against:
- [CLAUDE.md project instructions](./CLAUDE.md)
- [INITIAL-RESEARCH.md sections 9.1-9.7](./INITIAL-RESEARCH.md)
- [PLAN.md architecture overview](./PLAN.md)
