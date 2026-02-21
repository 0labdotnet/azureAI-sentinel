"""ChromaDB-backed vector store for incidents and playbooks.

Provides semantic search over historical incident data and investigation
playbooks using Azure OpenAI embeddings (text-embedding-3-large at 1024 dims).
"""

import logging

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from src.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-backed knowledge base for incidents and playbooks.

    Uses two separate collections (incidents, playbooks) with cosine distance
    and Azure OpenAI embeddings. Supports dependency injection of ChromaDB
    client for testing with EphemeralClient.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        client: chromadb.ClientAPI | None = None,
        embedding_fn: OpenAIEmbeddingFunction | None = None,
    ):
        if embedding_fn is None:
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
                path=settings.chromadb_path,
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
        """Format ChromaDB results with confidence flagging.

        Returns a dict with type, results list, low_confidence_warning, and
        total count. Each result item has document, metadata, and confidence
        ("normal" or "low"). Per user decision: distance/score is NOT included
        in the output.

        low_confidence_warning is True only when ALL results are low confidence.
        """
        items = []
        all_low = True  # Assume all low until proven otherwise

        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i]
                metadata = results["metadatas"][0][i]
                confidence = "low" if distance > threshold else "normal"
                if confidence == "normal":
                    all_low = False
                items.append({
                    "document": doc,
                    "metadata": metadata,
                    "confidence": confidence,
                })

        return {
            "type": result_type,
            "results": items,
            "low_confidence_warning": all_low and len(items) > 0,
            "total": len(items),
        }

    def get_collection_counts(self) -> dict:
        """Return document counts for both collections."""
        return {
            "incidents": self._incidents.count(),
            "playbooks": self._playbooks.count(),
        }
