"""Tests for MITRE ATT&CK fetcher in src/mitre.py.

Mocks HTTP requests with a minimal STIX bundle to test parsing,
caching, and graceful failure handling.
"""

from unittest.mock import MagicMock, patch

from src.mitre import CURATED_TECHNIQUE_IDS, fetch_mitre_techniques

# Minimal STIX bundle with 3 techniques:
# T1566 (Phishing) - in curated list
# T1078 (Valid Accounts) - in curated list
# T9999 (Fake Technique) - NOT in curated list
_MOCK_STIX_BUNDLE = {
    "type": "bundle",
    "id": "bundle--069d67fc-ffe7-4324-919b-cdf517a0339e",
    "objects": [
        {
            "type": "attack-pattern",
            "id": "attack-pattern--4d4baae1-2b18-42b1-b1d6-eb4ca1ace9d5",
            "created": "2023-01-01T00:00:00.000Z",
            "modified": "2023-01-01T00:00:00.000Z",
            "name": "Phishing",
            "description": "Adversaries may send phishing messages.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1566",
                    "url": "https://attack.mitre.org/techniques/T1566",
                }
            ],
            "kill_chain_phases": [
                {
                    "kill_chain_name": "mitre-attack",
                    "phase_name": "initial-access",
                }
            ],
            "x_mitre_is_subtechnique": False,
        },
        {
            "type": "attack-pattern",
            "id": "attack-pattern--5b7b92d5-642a-4d47-8424-62c1c371a733",
            "created": "2023-01-01T00:00:00.000Z",
            "modified": "2023-01-01T00:00:00.000Z",
            "name": "Valid Accounts",
            "description": "Adversaries may obtain and abuse valid accounts.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1078",
                    "url": "https://attack.mitre.org/techniques/T1078",
                }
            ],
            "kill_chain_phases": [
                {
                    "kill_chain_name": "mitre-attack",
                    "phase_name": "defense-evasion",
                },
                {
                    "kill_chain_name": "mitre-attack",
                    "phase_name": "initial-access",
                },
            ],
            "x_mitre_is_subtechnique": False,
        },
        {
            "type": "attack-pattern",
            "id": "attack-pattern--ea09d0a6-f8da-4bed-aba3-33a3888e6e62",
            "created": "2023-01-01T00:00:00.000Z",
            "modified": "2023-01-01T00:00:00.000Z",
            "name": "Fake Technique",
            "description": "This is NOT in the curated list.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T9999",
                    "url": "https://attack.mitre.org/techniques/T9999",
                }
            ],
            "kill_chain_phases": [
                {
                    "kill_chain_name": "mitre-attack",
                    "phase_name": "execution",
                }
            ],
            "x_mitre_is_subtechnique": False,
        },
        # A sub-technique that should be filtered out
        {
            "type": "attack-pattern",
            "id": "attack-pattern--cd289f0b-201c-460d-b0a8-4f13af3e45f2",
            "created": "2023-01-01T00:00:00.000Z",
            "modified": "2023-01-01T00:00:00.000Z",
            "name": "Spearphishing Attachment",
            "description": "Sub-technique of Phishing.",
            "external_references": [
                {
                    "source_name": "mitre-attack",
                    "external_id": "T1566.001",
                    "url": "https://attack.mitre.org/techniques/T1566/001",
                }
            ],
            "kill_chain_phases": [
                {
                    "kill_chain_name": "mitre-attack",
                    "phase_name": "initial-access",
                }
            ],
            "x_mitre_is_subtechnique": True,
        },
    ],
}


def _mock_response():
    """Create a mock requests.Response with the test STIX bundle."""
    mock = MagicMock()
    mock.json.return_value = _MOCK_STIX_BUNDLE
    mock.raise_for_status.return_value = None
    return mock


class TestFetchMitreTechniques:
    """Test fetch_mitre_techniques function."""

    @patch("src.mitre.requests.get")
    def test_returns_only_curated_techniques(self, mock_get):
        """Should return only the 2 techniques in the curated list."""
        mock_get.return_value = _mock_response()

        techniques = fetch_mitre_techniques()

        assert len(techniques) == 2
        ids = {t["technique_id"] for t in techniques}
        assert ids == {"T1566", "T1078"}

    @patch("src.mitre.requests.get")
    def test_technique_fields_populated(self, mock_get):
        """Each technique should have technique_id, name, description, tactics."""
        mock_get.return_value = _mock_response()

        techniques = fetch_mitre_techniques()

        phishing = next(t for t in techniques if t["technique_id"] == "T1566")
        assert phishing["name"] == "Phishing"
        assert "phishing" in phishing["description"].lower()
        assert "initial-access" in phishing["tactics"]

    @patch("src.mitre.requests.get")
    def test_caching_avoids_second_download(self, mock_get, tmp_path):
        """Second call with same cache_dir should use cache, not HTTP."""
        mock_get.return_value = _mock_response()
        cache_dir = str(tmp_path / "mitre_cache")

        # First call: downloads
        techniques_1 = fetch_mitre_techniques(cache_dir=cache_dir)
        assert mock_get.call_count == 1

        # Second call: uses cache
        techniques_2 = fetch_mitre_techniques(cache_dir=cache_dir)
        assert mock_get.call_count == 1  # Still 1 -- no second download

        assert len(techniques_1) == len(techniques_2)

    @patch("src.mitre.requests.get")
    def test_graceful_failure_on_connection_error(self, mock_get):
        """Network errors should return empty list, not raise."""
        mock_get.side_effect = ConnectionError("Network unreachable")

        techniques = fetch_mitre_techniques()

        assert techniques == []

    @patch("src.mitre.requests.get")
    def test_graceful_failure_on_parse_error(self, mock_get):
        """Invalid JSON should return empty list, not raise."""
        mock = MagicMock()
        mock.json.return_value = {"objects": "not-a-list"}
        mock.raise_for_status.return_value = None
        mock_get.return_value = mock

        techniques = fetch_mitre_techniques()

        assert techniques == []


class TestCuratedTechniqueIds:
    """Test the curated technique ID set."""

    def test_contains_25_techniques(self):
        assert len(CURATED_TECHNIQUE_IDS) == 25

    def test_all_ids_start_with_t(self):
        for tid in CURATED_TECHNIQUE_IDS:
            assert tid.startswith("T"), f"{tid} doesn't start with T"
