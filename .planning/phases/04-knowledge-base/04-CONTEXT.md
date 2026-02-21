# Phase 4: Knowledge Base - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

ChromaDB vector store providing historical incident search, MITRE ATT&CK-mapped investigation guidance, and playbook retrieval. Users query the knowledge base through the existing chatbot tool loop. Content is seeded from bundled samples + live Sentinel data + MITRE ATT&CK API. No write operations, no automated ingestion pipelines, no web UI.

</domain>

<decisions>
## Implementation Decisions

### Knowledge base content
- Seed with both synthetic sample incidents (bundled) and live Sentinel incidents (ingested)
- 15-25 synthetic incidents covering common attack types as the baseline dataset
- Auto-ingest live incidents from Sentinel on chatbot startup (no manual command needed)
- Ingest window: last 90 days of incidents from the Sentinel workspace
- Embeddings: text-embedding-3-large at 1024 dimensions (per CLAUDE.md design decision)

### Playbook sourcing
- Hand-written detailed playbooks for the top 5 most common incident types: phishing, brute force, malware, suspicious sign-in, data exfiltration
- MITRE ATT&CK-derived content for broader coverage beyond the top 5
- Each playbook is a detailed guide: step-by-step investigation, key indicators, escalation criteria, containment steps
- Playbooks include specific KQL queries the analyst can run manually during investigation

### Search result behavior
- Return top 3 results per knowledge base query
- Do not display similarity/confidence scores to the user
- If only low-confidence matches are found, warn the user about low confidence in the response
- Soft similarity threshold: return top results but flag anything below threshold as low confidence
- Separate result types: "Similar past incidents" and "Relevant playbooks" presented as distinct sections

### MITRE ATT&CK depth
- Curated subset of 20-30 most common techniques relevant to Sentinel detections (initial access, execution, persistence, lateral movement, etc.)
- Tagged mapping: each playbook and incident tagged with relevant ATT&CK technique IDs (e.g., T1566)
- Technique presentation: ID + name only (e.g., "T1566 - Phishing") — assumes SOC analyst familiarity
- Fetch MITRE data from ATT&CK STIX/TAXII API on startup — always current, no stale bundled data

### Claude's Discretion
- ChromaDB collection schema and metadata structure
- Chunking strategy for playbooks and incident descriptions
- Exact similarity threshold values
- Embedding pipeline implementation details
- How to handle startup failures (Sentinel unavailable, MITRE API down) gracefully
- MITRE technique selection criteria for the curated subset

</decisions>

<specifics>
## Specific Ideas

- Low-confidence warning behavior: when only weak matches exist, the chatbot should proactively tell the user rather than presenting poor results as authoritative
- Playbooks should feel actionable — not abstract guidance but specific steps a SOC analyst would follow, including KQL queries they can copy-paste into Sentinel
- MITRE techniques should be referenced concisely (ID + name) since the target audience is SOC professionals who know the framework

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-knowledge-base*
*Context gathered: 2026-02-20*
