---
phase: 04-knowledge-base
verified: 2026-02-20T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 4: Knowledge Base Verification Report

**Phase Goal:** Users can query historical incidents and investigation playbooks through the ChromaDB vector store, receiving MITRE ATT&CK-mapped guidance and pattern matching results
**Verified:** 2026-02-20
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Plan 01 must-haves verified (data layer):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | VectorStore creates two ChromaDB collections (incidents, playbooks) with cosine distance | VERIFIED | `src/vector_store.py` lines 50-59: `get_or_create_collection("incidents"/"playbooks", configuration={"hnsw": {"space": "cosine"}})` |
| 2 | Synthetic seed data contains 15-25 incidents covering common attack types | VERIFIED | `src/knowledge/seed_incidents.py`: exactly 20 incidents across 9 attack types (phishing x3, brute force x3, malware x3, suspicious sign-in x3, data exfiltration x2, privilege escalation x2, lateral movement x2, DoS x1, credential theft x1); confirmed by `python -c` output |
| 3 | Five hand-written playbooks cover phishing, brute force, malware, suspicious sign-in, and data exfiltration with actionable investigation steps and KQL queries | VERIFIED | `src/knowledge/playbooks.py` lines 9-418: 5 playbooks each with 4 sections; all investigation sections contain copy-pasteable KQL queries |
| 4 | MITRE ATT&CK fetcher downloads enterprise techniques from GitHub, filters to curated 25 techniques, and caches the result locally | VERIFIED | `src/mitre.py`: `CURATED_TECHNIQUE_IDS` set of 25; `_CACHE_TTL_SECONDS = 86400`; `_load_stix_data()` checks file age before downloading; all 7 MITRE tests pass |
| 5 | VectorStore search methods return top 3 results with low-confidence flagging at cosine distance threshold 0.35 | VERIFIED | `src/vector_store.py` lines 109-142: `_format_results(threshold=0.35)`; `confidence = "low" if distance > threshold else "normal"`; `low_confidence_warning = all_low and len(items) > 0`; confirmed by 4 `TestFormatResults` tests |
| 6 | Config Settings includes azure_openai_embedding_deployment and chromadb_path fields | VERIFIED | `src/config.py` lines 40-41: `azure_openai_embedding_deployment: str = "text-embedding-3-large"` and `chromadb_path: str = "./chroma_db"`; `load_settings()` reads env vars for both |

Plan 02 must-haves verified (integration layer):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | User can ask for investigation guidance and receive MITRE ATT&CK-mapped recommendations from the knowledge base | VERIFIED | `get_investigation_guidance` tool in `src/tools.py`; handler in `src/tool_handlers.py` combines playbook + incident search; wired through `ChatSession` to LLM |
| 8 | User can ask "have we seen this before?" and receive semantically matched historical incidents | VERIFIED | `search_similar_incidents` tool defined in `src/tools.py`; routed in `src/tool_handlers.py` to `_vector_store.search_similar_incidents()`; system prompt includes "have we seen this before?" guidance |
| 9 | User can ask about response procedures and receive playbook-based guidance | VERIFIED | `search_playbooks` tool defined in `src/tools.py`; routed in `src/tool_handlers.py` to `_vector_store.search_playbooks()`; system prompt includes "response procedure" guidance |
| 10 | Knowledge base tools are included in the ChatSession tool loop alongside Sentinel tools | VERIFIED | `src/openai_client.py` lines 80-83: `self._tools = SENTINEL_TOOLS + KB_TOOLS` when `vector_store is not None`; confirmed by `TestChatSessionWithVectorStore` tests verifying 8 vs 5 tool counts |
| 11 | Chatbot auto-ingests seed data, live Sentinel incidents, playbooks, and MITRE techniques on startup | VERIFIED | `src/main.py` `_init_knowledge_base()` function: upserts SEED_INCIDENTS, all PLAYBOOK chunks, live Sentinel incidents (last_30d, graceful failure), calls `fetch_mitre_techniques()` with cache dir |
| 12 | System prompt guides the LLM on when to use KB tools vs Sentinel tools | VERIFIED | `src/prompts.py` lines 86-100: distinct guidance entries for `search_similar_incidents`, `search_playbooks`, `get_investigation_guidance`; confirmed by assertion output |
| 13 | Search results present "Similar past incidents" and "Relevant playbooks" as distinct sections | VERIFIED | `src/prompts.py` lines 94-100: "Knowledge Base Result Presentation" section explicitly instructs the LLM to separate results into "Similar past incidents" and "Relevant playbooks" sections |
| 14 | Low-confidence matches produce a warning in the LLM's response | VERIFIED | `src/prompts.py` lines 97-100: "If results have a low_confidence_warning, inform the user that the matches may not be highly relevant and suggest refining their query"; `_format_results` populates this flag correctly |

**Score:** 14/14 truths verified

---

### Required Artifacts

#### Plan 01 Artifacts

| Artifact | Min Lines | Actual Lines | Status | Details |
|----------|-----------|-------------|--------|---------|
| `src/vector_store.py` | 80 | 149 | VERIFIED | VectorStore class with all 6 methods: `upsert_incidents`, `upsert_playbooks`, `search_similar_incidents`, `search_playbooks`, `_format_results`, `get_collection_counts`; imported in `src/tool_handlers.py` and `src/openai_client.py` |
| `src/knowledge/seed_incidents.py` | 100 | 345 | VERIFIED | 20 incident dicts; `build_incident_document()` and `build_incident_metadata()` helpers; imported in `src/main.py` |
| `src/knowledge/playbooks.py` | 200 | 448 | VERIFIED | 5 playbook dicts with 4 sections each (20 chunks total); `build_playbook_chunks()` helper; imported in `src/main.py` |
| `src/mitre.py` | 50 | 146 | VERIFIED | `fetch_mitre_techniques()` with caching; `CURATED_TECHNIQUE_IDS` set of 25; `stix2.MemoryStore` + `Filter` usage; imported in `src/main.py` |
| `tests/test_vector_store.py` | 50 | 279 | VERIFIED | 14 tests; `EphemeralClient` injection; `MockEmbeddingFunction`; all 14 pass |
| `tests/test_mitre.py` | 30 | 196 | VERIFIED | 7 tests covering curated list, caching, graceful failure; all 7 pass |

#### Plan 02 Artifacts

| Artifact | Required Content | Status | Details |
|----------|-----------------|--------|---------|
| `src/tools.py` | `KB_TOOLS` list with 3 tool definitions | VERIFIED | Lines 264-346: `KB_TOOLS` with `search_similar_incidents`, `search_playbooks`, `get_investigation_guidance`; each has required `query` string param; `get_tool_names()` returns 8 names |
| `src/tool_handlers.py` | `search_similar_incidents` routing to VectorStore | VERIFIED | Lines 167-212: three KB handler methods; `_vector_store.search_similar_incidents()` and `_vector_store.search_playbooks()` called directly; graceful `None` fallback in each handler |
| `src/prompts.py` | "knowledge base" guidance in SYSTEM_PROMPT | VERIFIED | Lines 86-100: distinct KB guidance section; all three KB tool names present |
| `src/openai_client.py` | `KB_TOOLS` import and combined tool list | VERIFIED | Line 23: `from src.tools import KB_TOOLS, SENTINEL_TOOLS`; lines 80-83: combined tool list conditional on `vector_store` |
| `src/main.py` | `VectorStore` initialization in startup pipeline | VERIFIED | Lines 28-132: `_init_knowledge_base()` creates `VectorStore`, ingests seed data, playbooks, live incidents, MITRE techniques; returns `None` on failure for graceful degradation |

---

### Key Link Verification

#### Plan 01 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `src/vector_store.py` | `src/config.py` | `settings.azure_openai_embedding_deployment` and `settings.chromadb_path` | VERIFIED | Lines 34-48: `settings.azure_openai_embedding_deployment` passed to `OpenAIEmbeddingFunction`; `settings.chromadb_path` passed to `PersistentClient` |
| `src/vector_store.py` | chromadb | `PersistentClient` and `OpenAIEmbeddingFunction` | VERIFIED | Lines 9-10: `import chromadb`; `from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction`; both used in constructor |
| `src/mitre.py` | stix2 | `MemoryStore` and `Filter` for ATT&CK data | VERIFIED | Line 14: `from stix2 import Filter, MemoryStore`; line 116: `MemoryStore(stix_data=..., allow_custom=True)`; lines 119-122: `src.query([Filter(...)])` |

#### Plan 02 Key Links

| From | To | Via | Status | Evidence |
|------|-----|-----|--------|---------|
| `src/tool_handlers.py` | `src/vector_store.py` | `_vector_store.search_similar_incidents` and `_vector_store.search_playbooks` | VERIFIED | Lines 176, 186, 198-203: direct calls to both VectorStore methods |
| `src/openai_client.py` | `src/tools.py` | `SENTINEL_TOOLS + KB_TOOLS` passed to `chat.completions.create()` | VERIFIED | Line 23: import; line 81: `self._tools = SENTINEL_TOOLS + KB_TOOLS`; line 119: `tools=self._tools` in API call |
| `src/main.py` | `src/vector_store.py` | Startup creates VectorStore and runs ingestion | VERIFIED | Lines 41, 45, 62, 68: `from src.vector_store import VectorStore`; `VectorStore(settings)`; `upsert_incidents(...)`; `upsert_playbooks(...)` |
| `src/main.py` | `src/mitre.py` | Startup fetches MITRE techniques | VERIFIED | Line 40: `from src.mitre import fetch_mitre_techniques`; line 113: `fetch_mitre_techniques(cache_dir=cache_dir)` |
| `src/prompts.py` | LLM behavior | KB guidance directs LLM to use KB tools | VERIFIED | All three KB tool names (`search_similar_incidents`, `search_playbooks`, `get_investigation_guidance`) appear in SYSTEM_PROMPT with usage guidance |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| KB-01 | 04-01-PLAN, 04-02-PLAN | User can ask for investigation guidance for a specific incident type and receive MITRE ATT&CK-mapped recommendations retrieved from the knowledge base | SATISFIED | `get_investigation_guidance` tool combines playbook and incident search; MITRE technique IDs embedded in playbook/incident metadata; system prompt directs LLM to use this tool for ATT&CK questions |
| KB-02 | 04-01-PLAN, 04-02-PLAN | User can ask "have we seen this type of attack before?" and the chatbot searches historical incidents for similar patterns | SATISFIED | `search_similar_incidents` tool with ChromaDB cosine similarity; 20 synthetic seed incidents ingested; live Sentinel incidents ingested at startup; system prompt explicitly covers "have we seen this before?" |
| KB-03 | 04-01-PLAN, 04-02-PLAN | User can ask about investigation procedures (e.g., "what's the response procedure for phishing?") and receive playbook-based guidance from the knowledge base | SATISFIED | `search_playbooks` tool; 5 hand-written playbooks with investigation/indicators/containment/escalation sections and KQL queries; 20 chunks ingested to ChromaDB; system prompt covers "response procedure" |

All three KB requirements accounted for in PLAN frontmatter. No orphaned requirements detected.

---

### Anti-Patterns Found

No anti-patterns detected. Scanned all 9 source files modified in Phase 4:
- No TODO/FIXME/HACK/PLACEHOLDER comments
- No stub return values (`return null`, empty dicts/lists without logic)
- No console.log-only implementations
- All methods contain substantive implementation

---

### Human Verification Required

The following behavior can only be verified by running the chatbot against a live Azure environment:

**1. End-to-end KB query flow**

**Test:** Run `python -m src.main`, then ask: "have we seen any phishing attacks before?"
**Expected:** LLM calls `search_similar_incidents`, retrieves matching synthetic incidents, presents them under "Similar past incidents" heading
**Why human:** Requires live Azure OpenAI + ChromaDB working together; embeddings must match semantically

**2. Playbook retrieval with KQL**

**Test:** Ask: "what is the response procedure for brute force?"
**Expected:** LLM calls `search_playbooks`, returns brute force playbook content including the KQL query from the investigation section
**Why human:** Requires live embedding retrieval to verify semantic matching works correctly

**3. MITRE guidance synthesis**

**Test:** Ask: "what MITRE techniques are involved in credential theft attacks?"
**Expected:** LLM calls `get_investigation_guidance`, returns combined playbook and incident results with ATT&CK technique IDs mentioned
**Why human:** Requires live session to verify LLM correctly synthesizes the combined result format

**4. Low-confidence warning behavior**

**Test:** Ask about an obscure or off-topic subject (e.g., "find incidents about quantum computing attacks")
**Expected:** LLM receives a `low_confidence_warning: true` result and informs the user the matches may not be relevant
**Why human:** Requires live embedding similarity to confirm the threshold produces a warning in practice

**5. Graceful KB degradation**

**Test:** Set `CHROMADB_PATH` to an unwritable path, then run the chatbot
**Expected:** Startup prints "Knowledge base unavailable -- running with Sentinel tools only."; chatbot functions using only Sentinel tools
**Why human:** Requires environment manipulation to test the degradation path

---

### Gaps Summary

No gaps. All 14 must-have truths are VERIFIED, all artifacts exist and are substantive, all key links are confirmed wired by direct code inspection. The full KB tool chain is end-to-end connected: ChromaDB collections created with cosine distance, seed data and playbooks ingestible, MITRE fetcher caches correctly, 3 KB tools exposed to the LLM, ToolDispatcher routes to VectorStore methods, system prompt guides tool selection, and startup pipeline initializes everything with graceful degradation.

The test suite confirms correctness programmatically: 21 new vector store and MITRE tests pass, plus 76 Plan 02 integration tests covering tool definitions, dispatcher routing, KB dispatch with and without VectorStore, and ChatSession tool count validation. All commit hashes documented in SUMMARYs verified in git log (c9391ce, 6427d33, 77b7a20, 7ea6e60).

---

_Verified: 2026-02-20_
_Verifier: Claude (gsd-verifier)_
