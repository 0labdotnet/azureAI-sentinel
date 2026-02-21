# Phase 4: Knowledge Base - Research

**Researched:** 2026-02-20
**Domain:** ChromaDB vector store, Azure OpenAI embeddings, MITRE ATT&CK data, knowledge base architecture
**Confidence:** HIGH

## Summary

Phase 4 adds a ChromaDB-backed knowledge base to the existing Sentinel chatbot, enabling three new capabilities: historical incident search, MITRE ATT&CK-mapped investigation guidance, and playbook retrieval. The implementation requires a new `vector_store.py` module, new tool definitions and tool handlers, seed data (synthetic incidents + hand-written playbooks), startup-time ingestion of live Sentinel incidents and MITRE ATT&CK techniques, and Azure OpenAI embeddings via `text-embedding-3-large` at 1024 dimensions.

ChromaDB v1.5.x is the standard local vector store for Python POCs. It supports persistent storage, metadata filtering, custom embedding functions (including Azure OpenAI), and cosine similarity distance. The project should use ChromaDB's built-in OpenAI embedding function for automatic embedding on add/query, configured for Azure OpenAI with the `dimensions` parameter set to 1024. The MITRE ATT&CK data should be fetched from the `attack-stix-data` GitHub repository using the `stix2` library (v3.0.2), filtered to a curated subset of 20-30 enterprise techniques.

**Primary recommendation:** Use ChromaDB `PersistentClient` with two separate collections (`incidents` and `playbooks`), cosine distance, and the built-in `OpenAIEmbeddingFunction` configured for Azure. Generate embeddings automatically via ChromaDB's embedding function (no manual embedding calls needed). Fetch MITRE ATT&CK data from GitHub on startup using `stix2.MemoryStore`. Add three new tools to the existing tool loop: `search_similar_incidents`, `search_playbooks`, and `get_investigation_guidance`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Seed with both synthetic sample incidents (bundled) and live Sentinel incidents (ingested)
- 15-25 synthetic incidents covering common attack types as the baseline dataset
- Auto-ingest live incidents from Sentinel on chatbot startup (no manual command needed)
- Ingest window: last 90 days of incidents from the Sentinel workspace
- Embeddings: text-embedding-3-large at 1024 dimensions (per CLAUDE.md design decision)
- Hand-written detailed playbooks for the top 5 most common incident types: phishing, brute force, malware, suspicious sign-in, data exfiltration
- MITRE ATT&CK-derived content for broader coverage beyond the top 5
- Each playbook is a detailed guide: step-by-step investigation, key indicators, escalation criteria, containment steps
- Playbooks include specific KQL queries the analyst can run manually during investigation
- Return top 3 results per knowledge base query
- Do not display similarity/confidence scores to the user
- If only low-confidence matches are found, warn the user about low confidence in the response
- Soft similarity threshold: return top results but flag anything below threshold as low confidence
- Separate result types: "Similar past incidents" and "Relevant playbooks" presented as distinct sections
- Curated subset of 20-30 most common techniques relevant to Sentinel detections (initial access, execution, persistence, lateral movement, etc.)
- Tagged mapping: each playbook and incident tagged with relevant ATT&CK technique IDs (e.g., T1566)
- Technique presentation: ID + name only (e.g., "T1566 - Phishing") -- assumes SOC analyst familiarity
- Fetch MITRE data from ATT&CK STIX/TAXII API on startup -- always current, no stale bundled data

### Claude's Discretion
- ChromaDB collection schema and metadata structure
- Chunking strategy for playbooks and incident descriptions
- Exact similarity threshold values
- Embedding pipeline implementation details
- How to handle startup failures (Sentinel unavailable, MITRE API down) gracefully
- MITRE technique selection criteria for the curated subset

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KB-01 | User can ask for investigation guidance for a specific incident type and receive MITRE ATT&CK-mapped recommendations from the knowledge base | Playbook collection with MITRE technique metadata; `search_playbooks` tool returning MITRE-tagged guidance; MITRE data fetched via stix2 from GitHub |
| KB-02 | User can ask "have we seen this type of attack before?" and the chatbot searches historical incidents for similar patterns | Incidents collection with semantic search via `search_similar_incidents` tool; live Sentinel incident ingestion + synthetic seed data; cosine similarity with top-3 results |
| KB-03 | User can ask about investigation procedures and receive playbook-based guidance from the knowledge base | Hand-written playbooks for top 5 incident types stored in playbooks collection; `search_playbooks` tool dispatched by LLM; playbooks chunked for retrieval quality |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| chromadb | >=1.5.0 | Local persistent vector store | Zero-config, built-in metadata filtering, persistence, embedding function integration; recommended for POC in INITIAL-RESEARCH.md |
| stix2 | >=3.0.2 | Parse MITRE ATT&CK STIX data | Official OASIS library for STIX 2.1; used by mitre-attack/attack-stix-data |
| openai | >=2.21.0 | Azure OpenAI embeddings via `client.embeddings.create()` | Already in requirements.txt; supports `dimensions` parameter for text-embedding-3 models |
| requests | >=2.31.0 | Fetch MITRE ATT&CK JSON from GitHub | Lightweight HTTP client for downloading STIX data bundle |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | (transitive) | ChromaDB returns float32 arrays | Comes with chromadb; no explicit install needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ChromaDB built-in OpenAI EF | Manual `client.embeddings.create()` calls | Manual approach gives more control but requires managing embedding calls in add/query; built-in EF is simpler and less error-prone |
| STIX TAXII server | GitHub raw JSON file | TAXII server requires `taxii2-client` dependency and may have availability issues; GitHub raw file is more reliable and simpler |
| Separate collection per data type | Single unified collection | Two collections (incidents + playbooks) allows different metadata schemas and separate result presentation per CONTEXT.md decision |

**Installation:**
```bash
pip install chromadb>=1.5.0 stix2>=3.0.2 requests>=2.31.0
```

Note: `requests` may already be a transitive dependency but should be listed explicitly in requirements.txt.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── vector_store.py       # VectorStore class: ChromaDB client, collections, add/query methods
├── knowledge/            # Static seed data
│   ├── __init__.py
│   ├── seed_incidents.py # 15-25 synthetic incident dicts
│   └── playbooks.py      # 5 hand-written playbooks as structured dicts
├── mitre.py              # MITRE ATT&CK data fetcher and technique mapper
├── tools.py              # UPDATED: add KB tool definitions alongside Sentinel tools
├── tool_handlers.py      # UPDATED: ToolDispatcher routes KB tools to VectorStore
├── openai_client.py      # UPDATED: pass all tools (Sentinel + KB) to chat.completions
├── config.py             # UPDATED: add embedding deployment + ChromaDB path settings
├── main.py               # UPDATED: initialize VectorStore + startup ingestion
└── prompts.py            # UPDATED: system prompt includes KB tool guidance
```

### Pattern 1: Two-Collection Schema

**What:** Separate ChromaDB collections for incidents and playbooks with distinct metadata schemas.

**When to use:** When result types need to be presented separately (per CONTEXT.md: "Similar past incidents" and "Relevant playbooks" as distinct sections).

**Schema -- Incidents Collection:**
```python
# Collection: "incidents"
# Distance: cosine
# Documents: natural-language incident description text
# Metadata per document:
{
    "incident_number": 42,           # int - Sentinel incident number (0 for synthetic)
    "title": "Suspicious Login",     # str - incident title
    "severity": "High",              # str - High/Medium/Low/Informational
    "status": "Closed",              # str - New/Active/Closed
    "source": "sentinel",            # str - "sentinel" or "synthetic"
    "mitre_techniques": "T1078,T1110",  # str - comma-separated technique IDs
    "created_date": "2026-01-15",    # str - ISO date for filtering
}
# IDs: "incident-{number}" for Sentinel, "synthetic-{index}" for seed data
```

**Schema -- Playbooks Collection:**
```python
# Collection: "playbooks"
# Distance: cosine
# Documents: playbook text chunk (investigation steps, KQL queries, etc.)
# Metadata per document:
{
    "playbook_id": "phishing-01",     # str - unique playbook identifier
    "incident_type": "Phishing",      # str - the attack type this playbook covers
    "mitre_techniques": "T1566,T1534",  # str - comma-separated technique IDs
    "section": "investigation",       # str - investigation/indicators/containment/escalation
    "chunk_index": 0,                 # int - ordering within playbook
    "source": "hand-written",         # str - "hand-written" or "mitre-derived"
}
```

### Pattern 2: Bring Your Own Embeddings via ChromaDB OpenAI EF

**What:** Use ChromaDB's built-in `OpenAIEmbeddingFunction` configured for Azure OpenAI to auto-embed documents on `add()` and queries on `query()`.

**When to use:** Always -- avoids manual embedding management and ensures consistent embedding model/dimensions between ingestion and retrieval.

**Example:**
```python
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Configure Azure OpenAI embedding function
embedding_fn = OpenAIEmbeddingFunction(
    api_key=settings.azure_openai_api_key,
    api_base=settings.azure_openai_endpoint,
    api_type="azure",
    api_version=settings.azure_openai_api_version,
    model_name=settings.azure_openai_embedding_deployment,  # "text-embedding-3-large"
    dimensions=1024,  # Truncated from 3072 per design decision
)

client = chromadb.PersistentClient(path=settings.chromadb_path)

incidents = client.get_or_create_collection(
    name="incidents",
    embedding_function=embedding_fn,
    configuration={"hnsw": {"space": "cosine"}},
)

playbooks = client.get_or_create_collection(
    name="playbooks",
    embedding_function=embedding_fn,
    configuration={"hnsw": {"space": "cosine"}},
)
```

### Pattern 3: Startup Ingestion Pipeline

**What:** On chatbot startup, ingest live Sentinel incidents (last 90 days) and MITRE ATT&CK techniques. Use `upsert()` for idempotency.

**When to use:** Every startup -- `upsert()` handles deduplication naturally.

**Example:**
```python
# In main.py startup sequence:
# 1. Initialize VectorStore (creates/opens ChromaDB collections)
# 2. Load synthetic seed data (upsert -- idempotent)
# 3. Fetch live Sentinel incidents (last 90 days, upsert by incident number)
# 4. Fetch MITRE ATT&CK techniques (upsert by technique ID)
# 5. Load hand-written playbooks (upsert -- idempotent)

# All ingestion uses upsert() so re-runs don't create duplicates
incidents_collection.upsert(
    ids=[f"incident-{inc['number']}" for inc in sentinel_incidents],
    documents=[build_incident_document(inc) for inc in sentinel_incidents],
    metadatas=[build_incident_metadata(inc) for inc in sentinel_incidents],
)
```

### Pattern 4: Tool Result Formatting for LLM

**What:** Knowledge base query results are returned as structured dicts matching the existing `QueryResult`-style pattern (with metadata envelope), so the LLM can synthesize them alongside Sentinel live data.

**When to use:** All KB tool responses.

**Example:**
```python
def search_similar_incidents(self, query: str, n_results: int = 3) -> dict:
    results = self._incidents.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    # Check soft threshold
    items = []
    low_confidence = False
    threshold = 0.35  # cosine distance threshold (lower = more similar)

    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        metadata = results["metadatas"][0][i]
        confidence = "low" if distance > threshold else "normal"
        if distance > threshold:
            low_confidence = True
        items.append({
            "document": doc,
            "metadata": metadata,
            "confidence": confidence,
        })

    return {
        "type": "similar_incidents",
        "results": items,
        "low_confidence_warning": low_confidence,
        "total": len(items),
    }
```

### Pattern 5: MITRE ATT&CK Data Fetching

**What:** Fetch enterprise ATT&CK techniques from GitHub using `stix2.MemoryStore`, filter to curated subset of 20-30 techniques.

**When to use:** On startup, to enrich playbooks and incidents with current technique data.

**Example:**
```python
import requests
from stix2 import MemoryStore, Filter

def fetch_mitre_techniques() -> list[dict]:
    """Fetch enterprise ATT&CK techniques from GitHub."""
    url = (
        "https://raw.githubusercontent.com/mitre-attack/attack-stix-data"
        "/master/enterprise-attack/enterprise-attack.json"
    )
    stix_json = requests.get(url, timeout=30).json()
    src = MemoryStore(stix_data=stix_json["objects"])

    # Get all techniques (not sub-techniques)
    techniques = src.query([
        Filter("type", "=", "attack-pattern"),
        Filter("x_mitre_is_subtechnique", "=", False),
    ])

    # Extract ID + name
    result = []
    for tech in techniques:
        ext_refs = tech.get("external_references", [])
        attack_id = next(
            (ref["external_id"] for ref in ext_refs
             if ref.get("source_name") == "mitre-attack"),
            None,
        )
        if attack_id:
            result.append({
                "technique_id": attack_id,
                "name": tech["name"],
                "description": tech.get("description", ""),
                "tactics": [
                    phase["phase_name"]
                    for phase in tech.get("kill_chain_phases", [])
                ],
            })
    return result
```

### Anti-Patterns to Avoid

- **Embedding model mismatch:** Never use different embedding models or different dimension settings for ingestion vs. retrieval. The ChromaDB `OpenAIEmbeddingFunction` on the collection ensures consistency automatically.
- **Storing raw KQL in embeddings:** KQL query syntax embedded as text will produce poor similarity matches. Store KQL queries in metadata or playbook text context, not as standalone embedded documents.
- **Freeform metadata values:** Use consistent, enumerated values for metadata fields (severity, source, section). Inconsistent casing or spelling breaks `where` filtering.
- **Blocking startup on external failures:** If Sentinel or MITRE API is down, the chatbot should still start with whatever data is already persisted in ChromaDB. Log warnings, don't crash.
- **Creating a new collection on every startup:** Use `get_or_create_collection()` not `create_collection()` to avoid errors on restart.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedding generation | Manual HTTP calls to Azure OpenAI embeddings API | ChromaDB `OpenAIEmbeddingFunction` with Azure config | Handles batching, retries, dimension truncation; consistent between add and query |
| Vector similarity search | numpy dot product or manual cosine distance | ChromaDB `collection.query()` | HNSW index, metadata filtering, pagination built-in |
| STIX data parsing | Manual JSON parsing of ATT&CK objects | `stix2.MemoryStore` + `stix2.Filter` | Handles STIX 2.1 schema validation, relationship traversal, deprecation filtering |
| Document deduplication | Custom ID checking before insert | ChromaDB `upsert()` | Atomic insert-or-update by ID, no race conditions |
| Incident text serialization | f-string concatenation | A dedicated `build_incident_document()` function | Ensures consistent format for embedding quality; single place to change format |

**Key insight:** ChromaDB's embedding function integration eliminates the entire "embed then store" pipeline. Documents go in as text, come out as text. The vector operations are invisible.

## Common Pitfalls

### Pitfall 1: ChromaDB Default Distance is L2, Not Cosine
**What goes wrong:** ChromaDB defaults to squared L2 distance. OpenAI `text-embedding-3-large` embeddings are designed for cosine similarity. Using L2 produces suboptimal ranking.
**Why it happens:** Collection created without explicit `configuration={"hnsw": {"space": "cosine"}}`.
**How to avoid:** Always specify `configuration={"hnsw": {"space": "cosine"}}` on collection creation.
**Warning signs:** Search results seem poorly ranked despite good queries.

### Pitfall 2: Embedding Dimension Mismatch
**What goes wrong:** Ingestion uses 1024 dimensions but query uses 3072 (or vice versa), causing zero or garbage results.
**Why it happens:** Inconsistent `dimensions` parameter between code paths.
**How to avoid:** Use a single `OpenAIEmbeddingFunction` instance shared by the collection. ChromaDB handles both add and query embedding automatically.
**Warning signs:** ChromaDB raises dimension mismatch error, or results have very high distances.

### Pitfall 3: ChromaDB OpenAI EF Requires `deployment_id` for Azure
**What goes wrong:** Azure OpenAI requires `deployment_id` (the deployment name), not just `model_name`.
**Why it happens:** The ChromaDB OpenAI embedding function checks `api_type == "azure"` and requires `deployment_id`, `api_version`, and `api_base`.
**How to avoid:** Pass all Azure-specific params: `api_type="azure"`, `api_base=endpoint`, `api_version=version`, `deployment_id=deployment_name`, and also set `model_name` to the deployment name.
**Warning signs:** Authentication errors or 404 from Azure OpenAI when adding documents.

### Pitfall 4: MITRE ATT&CK JSON Download is ~30MB
**What goes wrong:** Startup takes 5-10 seconds to download the full enterprise-attack.json (approximately 30MB).
**Why it happens:** The full ATT&CK dataset includes all objects (techniques, mitigations, data sources, relationships, etc.).
**How to avoid:** Cache the download locally with a TTL (e.g., 24 hours). On startup, use cached copy if fresh enough; re-download if stale. A simple file timestamp check suffices for POC.
**Warning signs:** Slow startup, or startup failures when GitHub is unreachable.

### Pitfall 5: ChromaDB Add/Upsert Batch Size
**What goes wrong:** Adding thousands of documents in one call can cause memory issues or timeouts.
**Why it happens:** Each document needs embedding via Azure OpenAI API call. Large batches exceed rate limits.
**How to avoid:** Batch upserts in groups of 50-100 documents. Azure OpenAI embedding API supports array inputs (up to 2048 items per request, but rate limits may constrain this).
**Warning signs:** Rate limit (429) errors from Azure OpenAI during startup ingestion.

### Pitfall 6: Playbook Chunking Destroys Context
**What goes wrong:** Splitting a playbook into tiny chunks loses the coherent investigation flow. The LLM receives a fragment like "Step 3: Check the SigninLogs" without knowing which investigation it belongs to.
**Why it happens:** Overly aggressive chunking (e.g., 200-token chunks).
**How to avoid:** Chunk by logical section (investigation steps, key indicators, containment, escalation) rather than by token count. Each chunk should include the playbook title and incident type in the document text for self-contained context. Target 300-600 tokens per chunk with section-based boundaries.
**Warning signs:** Playbook search results feel disconnected or missing context.

### Pitfall 7: Soft Threshold Tuning
**What goes wrong:** Cosine distance threshold is too aggressive (flagging everything as low confidence) or too permissive (never warning).
**Why it happens:** Cosine distance values depend on the embedding model and content domain. Generic thresholds from tutorials don't apply.
**How to avoid:** Start with a cosine distance threshold of ~0.35 (moderate). Test with representative queries and adjust. Remember: cosine distance of 0.0 = perfect match, 1.0 = orthogonal, 2.0 = opposite.
**Warning signs:** Every query gets a low-confidence warning, or obviously weak matches appear without warning.

## Code Examples

### VectorStore Class Structure
```python
# Source: Pattern derived from ChromaDB docs + project architecture
import logging
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from src.config import Settings

logger = logging.getLogger(__name__)

class VectorStore:
    """ChromaDB-backed knowledge base for incidents and playbooks."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: chromadb.ClientAPI | None = None,
    ):
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=settings.azure_openai_api_key,
            api_base=settings.azure_openai_endpoint,
            api_type="azure",
            api_version=settings.azure_openai_api_version,
            model_name=settings.azure_openai_embedding_deployment,
            deployment_id=settings.azure_openai_embedding_deployment,
            dimensions=1024,
        )

        if client is not None:
            self._client = client
        else:
            self._client = chromadb.PersistentClient(
                path=settings.chromadb_path
            )

        self._incidents = self._client.get_or_create_collection(
            name="incidents",
            embedding_function=embedding_fn,
            configuration={"hnsw": {"space": "cosine"}},
        )
        self._playbooks = self._client.get_or_create_collection(
            name="playbooks",
            embedding_function=embedding_fn,
            configuration={"hnsw": {"space": "cosine"}},
        )

    def upsert_incidents(self, incidents: list[dict]) -> int:
        """Upsert incident documents. Returns count upserted."""
        if not incidents:
            return 0
        self._incidents.upsert(
            ids=[inc["id"] for inc in incidents],
            documents=[inc["document"] for inc in incidents],
            metadatas=[inc["metadata"] for inc in incidents],
        )
        return len(incidents)

    def upsert_playbooks(self, chunks: list[dict]) -> int:
        """Upsert playbook chunks. Returns count upserted."""
        if not chunks:
            return 0
        self._playbooks.upsert(
            ids=[ch["id"] for ch in chunks],
            documents=[ch["document"] for ch in chunks],
            metadatas=[ch["metadata"] for ch in chunks],
        )
        return len(chunks)

    def search_similar_incidents(
        self, query: str, n_results: int = 3
    ) -> dict:
        """Search for similar historical incidents."""
        results = self._incidents.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(
            results, result_type="similar_incidents"
        )

    def search_playbooks(
        self, query: str, n_results: int = 3
    ) -> dict:
        """Search for relevant playbooks."""
        results = self._playbooks.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(
            results, result_type="playbooks"
        )

    def _format_results(
        self, results: dict, result_type: str, threshold: float = 0.35
    ) -> dict:
        """Format ChromaDB results with confidence flagging."""
        items = []
        low_confidence = True  # Assume low until proven otherwise

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                metadata = results["metadatas"][0][i]
                confidence = "low" if distance > threshold else "normal"
                if confidence == "normal":
                    low_confidence = False
                items.append({
                    "document": doc,
                    "metadata": metadata,
                    "confidence": confidence,
                })

        return {
            "type": result_type,
            "results": items,
            "low_confidence_warning": low_confidence and len(items) > 0,
            "total": len(items),
        }

    def get_collection_counts(self) -> dict:
        """Return document counts for both collections."""
        return {
            "incidents": self._incidents.count(),
            "playbooks": self._playbooks.count(),
        }
```

### New Tool Definitions (to add to tools.py)
```python
# Source: Follows existing SENTINEL_TOOLS pattern in src/tools.py
KB_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_similar_incidents",
            "description": (
                "Search the knowledge base for historical incidents "
                "similar to a described attack pattern or incident type. "
                "Use this when the user asks 'have we seen this before?', "
                "'similar attacks', 'historical incidents like X', or "
                "wants to know about past occurrences of a threat type."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the attack "
                            "pattern or incident type to search for."
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
                "Search the knowledge base for investigation playbooks "
                "and response procedures. Use this when the user asks "
                "'how to investigate X', 'response procedure for Y', "
                "'investigation guidance', 'what should I do about Z', "
                "or any question about incident response steps."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description of the incident "
                            "type or investigation topic to find playbooks for."
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
                "Get MITRE ATT&CK-mapped investigation guidance for a "
                "specific incident type or technique. Use this when the "
                "user asks about MITRE techniques, ATT&CK mappings, "
                "'what techniques are involved in X', or wants "
                "structured investigation recommendations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The incident type, attack technique, or "
                            "MITRE ATT&CK technique ID to get guidance for."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
]
```

### Incident Document Builder
```python
def build_incident_document(incident: dict) -> str:
    """Convert an incident dict into a natural-language document for embedding.

    Structured fields become readable text to maximize embedding quality.
    """
    parts = [
        f"Security Incident: {incident.get('title', 'Unknown')}",
        f"Severity: {incident.get('severity', 'Unknown')}",
        f"Status: {incident.get('status', 'Unknown')}",
    ]
    if incident.get("description"):
        parts.append(f"Description: {incident['description']}")
    if incident.get("mitre_techniques"):
        parts.append(f"MITRE ATT&CK Techniques: {incident['mitre_techniques']}")
    if incident.get("entities"):
        parts.append(f"Affected Entities: {incident['entities']}")
    return "\n".join(parts)
```

### Azure OpenAI Embeddings (Direct Call Pattern)
```python
# Source: Azure OpenAI docs (learn.microsoft.com)
# This is what ChromaDB's OpenAIEmbeddingFunction does internally.
# Shown for reference -- the VectorStore should NOT call this directly.
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version=settings.azure_openai_api_version,
)

response = client.embeddings.create(
    input="Your text string goes here",
    model=settings.azure_openai_embedding_deployment,  # deployment name
    dimensions=1024,  # truncate from 3072
)

embedding_vector = response.data[0].embedding  # list[float] of length 1024
```

### Settings Updates
```python
# Fields to add to Settings dataclass in config.py:
azure_openai_embedding_deployment: str = "text-embedding-3-large"
chromadb_path: str = "./chroma_db"

# Add to OPTIONAL_VARS (already partially there):
# "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "Embedding model deployment name"
# "CHROMADB_PATH": "ChromaDB persistent storage directory"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| chromadb `metadata={"hnsw:space": "cosine"}` | `configuration={"hnsw": {"space": "cosine"}}` | ChromaDB ~0.5.x+ | New configuration API; old metadata-based config deprecated |
| `client.create_collection()` every time | `client.get_or_create_collection()` | ChromaDB 0.4+ | Idempotent collection creation |
| text-embedding-ada-002 (1536 fixed dims) | text-embedding-3-large (configurable dims) | OpenAI Jan 2024 | Better quality + configurable dimensions; use `dimensions=1024` |
| MITRE ATT&CK STIX 2.0 (mitre/cti repo) | STIX 2.1 (mitre-attack/attack-stix-data repo) | 2023 | Newer repo with STIX 2.1 format; use `attack-stix-data` not `cti` |
| stix2 v2.x | stix2 v3.0.2 | 2026-02-12 | Latest release; supports STIX 2.1 natively |

**Deprecated/outdated:**
- `chromadb.Client()` -- replaced by `PersistentClient()` or `EphemeralClient()`
- ChromaDB `metadata={"hnsw:space": ...}` -- replaced by `configuration={"hnsw": {"space": ...}}`
- `text-embedding-ada-002` -- legacy; replaced by text-embedding-3-small/large
- `mitre/cti` GitHub repo -- legacy STIX 2.0; use `mitre-attack/attack-stix-data` for STIX 2.1

## Discretionary Recommendations

These are areas where CONTEXT.md grants Claude's discretion. Here are researched recommendations:

### ChromaDB Collection Schema
**Recommendation:** Two collections (`incidents` and `playbooks`) as detailed in Pattern 1 above. Rationale: separate result presentation per CONTEXT.md, different metadata schemas, simpler queries.

### Chunking Strategy
**Recommendation:** Section-based chunking for playbooks (investigation, indicators, containment, escalation as separate chunks, each 300-600 tokens). Include playbook title and incident type in every chunk for self-contained context. Incidents should be single documents (each well under 8K token limit).

### Similarity Threshold
**Recommendation:** Start with cosine distance threshold of 0.35. Below 0.35 = normal confidence, above 0.35 = low confidence. This is moderate and can be tuned post-implementation. Note: ChromaDB returns cosine *distance* (0.0 = identical, 2.0 = opposite), not cosine *similarity* (1.0 = identical, -1.0 = opposite).

### Startup Failure Handling
**Recommendation:** Graceful degradation pattern:
1. If ChromaDB path is inaccessible: log error, disable KB tools, chatbot runs with Sentinel-only tools
2. If Sentinel is unavailable for ingestion: log warning, use whatever is already persisted in ChromaDB (synthetic + prior ingestions)
3. If MITRE ATT&CK GitHub is unreachable: log warning, use cached STIX file if available, skip MITRE enrichment if no cache
4. If Azure OpenAI embedding endpoint is down: log error, disable KB tools entirely (no embedding = no search)

### MITRE Technique Selection
**Recommendation:** Curate 25 techniques across 8 tactics most relevant to Sentinel SOC detections:
- **Initial Access:** T1566 (Phishing), T1078 (Valid Accounts), T1190 (Exploit Public-Facing App)
- **Execution:** T1059 (Command and Scripting Interpreter), T1204 (User Execution)
- **Persistence:** T1136 (Create Account), T1053 (Scheduled Task/Job), T1098 (Account Manipulation)
- **Privilege Escalation:** T1548 (Abuse Elevation Control), T1134 (Access Token Manipulation)
- **Defense Evasion:** T1562 (Impair Defenses), T1070 (Indicator Removal)
- **Credential Access:** T1110 (Brute Force), T1003 (OS Credential Dumping), T1558 (Steal Kerberos Ticket)
- **Lateral Movement:** T1021 (Remote Services), T1570 (Lateral Tool Transfer)
- **Collection/Exfiltration:** T1005 (Data from Local System), T1567 (Exfiltration Over Web Service), T1041 (Exfiltration Over C2)
- **Discovery:** T1087 (Account Discovery), T1069 (Permission Groups Discovery)
- **Impact:** T1486 (Data Encrypted for Impact), T1489 (Service Stop)
- **Command and Control:** T1071 (Application Layer Protocol)

This list covers the most commonly mapped techniques in Microsoft Sentinel's built-in detection rules.

## Testing Strategy Notes

- **VectorStore tests:** Use `chromadb.EphemeralClient()` for test injection (no disk persistence needed in tests). The constructor already supports optional `client` parameter following the project's dependency injection pattern.
- **MITRE fetcher tests:** Mock `requests.get()` with a small subset of STIX data (5-10 techniques).
- **Tool handler tests:** Mock VectorStore methods following the existing `mock_sentinel_client` pattern.
- **Integration test:** A smoke test that creates an ephemeral ChromaDB, adds a few incidents and playbooks, and verifies search returns relevant results.

## Open Questions

1. **ChromaDB `OpenAIEmbeddingFunction` Azure compatibility**
   - What we know: The source code shows Azure support with `api_type="azure"`, `api_base`, `api_version`, and `deployment_id` parameters. The `dimensions` parameter is supported for `text-embedding-3` models.
   - What's unclear: Whether ChromaDB v1.5.x specifically handles the Azure `/openai/v1/` endpoint path correctly, or if manual path construction is needed.
   - Recommendation: Test early in implementation. Fallback: if the built-in EF doesn't work with Azure, create a thin custom `EmbeddingFunction` wrapper that calls `AzureOpenAI.client.embeddings.create()` directly. This is ~20 lines of code.

2. **MITRE ATT&CK JSON download size and startup latency**
   - What we know: enterprise-attack.json is approximately 30MB. First startup will be slow.
   - What's unclear: Exact download time on the developer's network; whether caching is worth the complexity for a POC.
   - Recommendation: Implement a simple file cache with 24-hour TTL. Store downloaded JSON in `{chromadb_path}/mitre_cache/`. If file exists and is less than 24 hours old, use cached version.

3. **Exact number of Sentinel incidents to expect from 90-day window**
   - What we know: The existing `query_incidents()` method has a max limit of 100 results.
   - What's unclear: Whether 90 days of real Sentinel data will produce hundreds or thousands of incidents. The ingestion pipeline needs to handle pagination or accept a reasonable cap.
   - Recommendation: Use the existing SentinelClient to query incidents with `last_30d` time window (max available), run it 3 times with different date offsets, or accept a cap of ~200 incidents for the POC. The seed synthetic data provides baseline coverage regardless.

## Sources

### Primary (HIGH confidence)
- [ChromaDB Official Docs - Collection API](https://docs.trychroma.com/reference/python/collection) - Collection methods (add, query, upsert, get, delete)
- [ChromaDB Official Docs - Configure Collections](https://docs.trychroma.com/docs/collections/configure) - HNSW parameters, distance functions
- [ChromaDB Official Docs - OpenAI Integration](https://docs.trychroma.com/integrations/embedding-models/openai) - OpenAI embedding function with Azure support
- [ChromaDB GitHub - OpenAI EF Source](https://github.com/chroma-core/chroma/blob/main/chromadb/utils/embedding_functions/openai_embedding_function.py) - Verified dimensions parameter and Azure support
- [MITRE ATT&CK attack-stix-data USAGE.md](https://github.com/mitre-attack/attack-stix-data/blob/master/USAGE.md) - Python code patterns for loading ATT&CK data with stix2
- [Azure OpenAI Embeddings How-To](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/embeddings) - Official embeddings API documentation, updated 2026-02-10
- [stix2 v3.0.2 on PyPI](https://pypi.org/project/stix2/) - Latest version, released 2026-02-12
- [chromadb v1.5.1 on PyPI](https://pypi.org/project/chromadb/) - Latest version

### Secondary (MEDIUM confidence)
- [ChromaDB Metadata Filtering Docs](https://docs.trychroma.com/docs/querying-collections/metadata-filtering) - Where clause operators ($eq, $ne, $gt, $lt, $in, $nin, $and, $or)
- [ChromaDB Cookbook - Collections](https://cookbook.chromadb.dev/core/collections/) - get_or_create_collection patterns
- [Microsoft Sentinel MITRE Coverage](https://learn.microsoft.com/en-us/azure/sentinel/mitre-coverage) - Sentinel aligned to ATT&CK v18

### Tertiary (LOW confidence)
- Cosine distance threshold of 0.35 -- based on general RAG experience with OpenAI embeddings, not empirically validated for this specific domain. Needs tuning during implementation.
- MITRE technique curated list -- based on commonly referenced Sentinel detection techniques, but the exact list should be validated against actual Sentinel workspace detections.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - ChromaDB and stix2 verified via PyPI and official docs; OpenAI embeddings verified via Azure docs
- Architecture: HIGH - Patterns follow existing project conventions (dependency injection, tool dispatch, structured results); ChromaDB API verified
- Pitfalls: HIGH - Distance function default, dimension mismatch, Azure EF config all verified from source code and docs
- Discretionary items: MEDIUM - Threshold values and technique list need empirical validation

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days -- libraries are stable, MITRE ATT&CK updates quarterly)
