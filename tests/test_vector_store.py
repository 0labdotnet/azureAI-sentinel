"""Tests for VectorStore in src/vector_store.py.

Uses chromadb.EphemeralClient for test injection and a deterministic
mock embedding function to avoid Azure OpenAI calls during tests.
"""

import contextlib
import hashlib
from typing import Any

import chromadb
import pytest
from chromadb import Documents, EmbeddingFunction, Embeddings

from src.config import Settings
from src.vector_store import VectorStore


class MockEmbeddingFunction(EmbeddingFunction[Documents]):  # type: ignore[type-arg]
    """Deterministic embedding function for testing.

    Produces 1024-dimensional float vectors derived from a hash of the
    input text, ensuring consistent results without calling Azure OpenAI.
    Implements ChromaDB EmbeddingFunction protocol for v1.5.x.
    """

    def __init__(self) -> None:
        pass

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        return [self._embed(text) for text in input]

    @staticmethod
    def name() -> str:
        return "mock_embedding"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "MockEmbeddingFunction":
        return MockEmbeddingFunction()

    def get_config(self) -> dict[str, Any]:
        return {}

    def _embed(self, text: str) -> list[float]:
        """Create a deterministic 1024-dim vector from text hash."""
        digest = hashlib.sha256(text.encode()).digest()
        # Expand digest to fill 1024 floats
        values = []
        for i in range(1024):
            byte_idx = i % len(digest)
            values.append((digest[byte_idx] + i) % 256 / 255.0)
        return values


@pytest.fixture
def mock_settings():
    """Settings instance for VectorStore tests."""
    return Settings(
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="test-key",
        azure_openai_embedding_deployment="text-embedding-3-large",
        chromadb_path="./test_chroma_db",
    )


@pytest.fixture
def vector_store(mock_settings):
    """VectorStore with EphemeralClient and mock embeddings.

    Deletes existing collections before creating fresh ones to ensure
    test isolation (EphemeralClient shares state across instances).
    """
    client = chromadb.EphemeralClient()
    # Clean slate: delete collections if they exist from prior tests
    for name in ("incidents", "playbooks"):
        with contextlib.suppress(Exception):
            client.delete_collection(name)
    embedding_fn = MockEmbeddingFunction()
    return VectorStore(
        mock_settings,
        client=client,
        embedding_fn=embedding_fn,
    )


def _make_incident(incident_id: str, title: str) -> dict:
    """Helper to create an incident dict for upserting."""
    return {
        "id": incident_id,
        "document": f"Security Incident: {title}\nSeverity: High",
        "metadata": {
            "incident_number": 0,
            "title": title,
            "severity": "High",
            "status": "Active",
            "source": "synthetic",
            "mitre_techniques": "T1566",
            "created_date": "2026-02-20",
        },
    }


def _make_playbook_chunk(chunk_id: str, content: str) -> dict:
    """Helper to create a playbook chunk dict for upserting."""
    return {
        "id": chunk_id,
        "document": content,
        "metadata": {
            "playbook_id": "phishing-01",
            "incident_type": "Phishing",
            "mitre_techniques": "T1566",
            "section": "investigation",
            "chunk_index": 0,
            "source": "hand-written",
        },
    }


class TestUpsertIncidents:
    """Test upsert_incidents method."""

    def test_upsert_returns_count(self, vector_store):
        incidents = [
            _make_incident("inc-1", "Phishing attack"),
            _make_incident("inc-2", "Brute force attempt"),
            _make_incident("inc-3", "Malware detected"),
        ]
        count = vector_store.upsert_incidents(incidents)
        assert count == 3

    def test_upsert_empty_returns_zero(self, vector_store):
        assert vector_store.upsert_incidents([]) == 0

    def test_upsert_idempotent(self, vector_store):
        """Upserting same IDs again should not create duplicates."""
        incidents = [
            _make_incident("inc-1", "Phishing attack"),
            _make_incident("inc-2", "Brute force attempt"),
            _make_incident("inc-3", "Malware detected"),
        ]
        vector_store.upsert_incidents(incidents)
        vector_store.upsert_incidents(incidents)  # Second upsert
        counts = vector_store.get_collection_counts()
        assert counts["incidents"] == 3


class TestUpsertPlaybooks:
    """Test upsert_playbooks method."""

    def test_upsert_returns_count(self, vector_store):
        chunks = [
            _make_playbook_chunk("pb-1", "Phishing investigation steps"),
            _make_playbook_chunk("pb-2", "Brute force investigation steps"),
        ]
        count = vector_store.upsert_playbooks(chunks)
        assert count == 2

    def test_upsert_empty_returns_zero(self, vector_store):
        assert vector_store.upsert_playbooks([]) == 0


class TestSearchSimilarIncidents:
    """Test search_similar_incidents method."""

    def test_returns_results_with_correct_type(self, vector_store):
        incidents = [
            _make_incident("inc-1", "Phishing email with malicious attachment"),
            _make_incident("inc-2", "Brute force attack on VPN"),
            _make_incident("inc-3", "Ransomware execution blocked"),
        ]
        vector_store.upsert_incidents(incidents)

        result = vector_store.search_similar_incidents("phishing attack")
        assert result["type"] == "similar_incidents"
        assert isinstance(result["results"], list)
        assert result["total"] > 0

    def test_result_items_have_expected_keys(self, vector_store):
        incidents = [_make_incident("inc-1", "Phishing email")]
        vector_store.upsert_incidents(incidents)

        result = vector_store.search_similar_incidents("phishing", n_results=1)
        item = result["results"][0]
        assert "document" in item
        assert "metadata" in item
        assert "confidence" in item
        assert item["confidence"] in ("normal", "low")


class TestSearchPlaybooks:
    """Test search_playbooks method."""

    def test_returns_results_with_correct_type(self, vector_store):
        chunks = [
            _make_playbook_chunk("pb-1", "Phishing investigation playbook"),
            _make_playbook_chunk("pb-2", "Brute force response playbook"),
        ]
        vector_store.upsert_playbooks(chunks)

        result = vector_store.search_playbooks("phishing investigation")
        assert result["type"] == "playbooks"
        assert isinstance(result["results"], list)
        assert result["total"] > 0


class TestFormatResults:
    """Test _format_results low-confidence flagging."""

    def test_low_confidence_warning_when_all_high_distance(self, vector_store):
        """When all distances are above threshold, low_confidence_warning is True."""
        mock_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "val1"}, {"key": "val2"}]],
            "distances": [[0.8, 0.9]],  # Both above 0.35
        }
        formatted = vector_store._format_results(
            mock_results, result_type="test"
        )
        assert formatted["low_confidence_warning"] is True
        assert all(r["confidence"] == "low" for r in formatted["results"])

    def test_no_warning_when_some_normal_confidence(self, vector_store):
        """When at least one result is below threshold, no warning."""
        mock_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "val1"}, {"key": "val2"}]],
            "distances": [[0.1, 0.8]],  # One below, one above 0.35
        }
        formatted = vector_store._format_results(
            mock_results, result_type="test"
        )
        assert formatted["low_confidence_warning"] is False
        assert formatted["results"][0]["confidence"] == "normal"
        assert formatted["results"][1]["confidence"] == "low"

    def test_empty_results_no_warning(self, vector_store):
        """Empty results should not trigger low_confidence_warning."""
        mock_results = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        formatted = vector_store._format_results(
            mock_results, result_type="test"
        )
        assert formatted["low_confidence_warning"] is False
        assert formatted["total"] == 0

    def test_distance_score_not_in_output(self, vector_store):
        """Per user decision, distance/score should NOT be in the output."""
        mock_results = {
            "documents": [["doc1"]],
            "metadatas": [[{"key": "val"}]],
            "distances": [[0.2]],
        }
        formatted = vector_store._format_results(
            mock_results, result_type="test"
        )
        item = formatted["results"][0]
        assert "distance" not in item
        assert "score" not in item


class TestGetCollectionCounts:
    """Test get_collection_counts method."""

    def test_initial_counts_are_zero(self, vector_store):
        counts = vector_store.get_collection_counts()
        assert counts == {"incidents": 0, "playbooks": 0}

    def test_counts_after_upsert(self, vector_store):
        vector_store.upsert_incidents([
            _make_incident("inc-1", "Test incident"),
        ])
        vector_store.upsert_playbooks([
            _make_playbook_chunk("pb-1", "Test playbook"),
            _make_playbook_chunk("pb-2", "Another playbook"),
        ])
        counts = vector_store.get_collection_counts()
        assert counts == {"incidents": 1, "playbooks": 2}
