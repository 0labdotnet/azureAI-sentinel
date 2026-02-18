# Phase 1: Foundation - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Azure resource provisioning (OpenAI + Sentinel workspace), content filter modification request, Python project scaffolding with validated configuration loading. Both Azure OpenAI and Sentinel resources need to be created from scratch. Content filter modification process needs to be researched and submitted. Project targets Python 3.12 with `requirements.txt` dependency management.

</domain>

<decisions>
## Implementation Decisions

### Config validation scope
- `python -m src.config` performs layered validation: first checks all env vars are present, then attempts live connectivity only if env vars pass
- Env vars are grouped by phase: Phase 1 vars (Azure OpenAI endpoint, Sentinel workspace ID, auth) are required; later-phase vars (ChromaDB path, embedding config) are optional and noted as "not yet needed"
- On success, displays a summary table showing all checked items with pass/fail status (env vars loaded, OpenAI connected, Sentinel connected)
- On failure, shows all missing/invalid env vars at once (not fail-fast), but skips connectivity checks if env vars are incomplete

### Content filter handling
- If Azure OpenAI returns a content filter error during connectivity check, show a specific message: "Content filter modification pending — approval required before security queries work" (not a generic connection error)
- Create mock Azure OpenAI responses so development can continue during the 1-3 business day content filter approval window
- Mocks should cover: chat completion responses, tool call responses, and content filter rejection responses

### Developer setup flow
- Include a documented `.env.example` with every variable, grouped by service (Azure OpenAI, Sentinel, Auth), with inline comments explaining each variable and where to find the values in Azure portal
- Audience is a small team (2-3 developers) — setup docs should be clear but not enterprise-grade
- `python -m src.config` is the single verification command — no separate verify script needed
- Target Python 3.12 explicitly (document in README/pyproject)
- Use `requirements.txt` with pinned versions for dependency management

### Azure resource provisioning
- Neither Azure OpenAI nor Sentinel workspace exists yet — both must be provisioned as part of Phase 1
- Content filter modification request process needs to be researched (user hasn't gone through it before)
- Plan 01-01 should include step-by-step provisioning guidance and content filter submission instructions

### Claude's Discretion
- Exact table formatting for config validation output
- Mock response fixture design and storage location
- `.env.example` grouping order and comment style
- Error message wording for non-content-filter failures

</decisions>

<specifics>
## Specific Ideas

- Config validation should clearly distinguish between "env var missing" errors and "connectivity failed" errors — two separate validation layers
- Content filter error should be recognizable and actionable, not buried in a generic Azure SDK exception
- The `.env.example` should tell developers WHERE to find each value in Azure portal (e.g., "Find in Azure Portal > Resource Group > OpenAI resource > Keys and Endpoint")

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-17*
