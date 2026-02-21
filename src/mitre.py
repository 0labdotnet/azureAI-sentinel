"""MITRE ATT&CK technique fetcher with local file caching.

Downloads the enterprise ATT&CK dataset from GitHub, filters to a curated
subset of 25 techniques most relevant to Sentinel SOC detections, and
caches the raw JSON locally with a 24-hour TTL.
"""

import json
import logging
import time
from pathlib import Path

import requests
from stix2 import Filter, MemoryStore

logger = logging.getLogger(__name__)

# Curated 25 techniques across 8+ tactics most relevant to Sentinel detections
CURATED_TECHNIQUE_IDS: set[str] = {
    # Initial Access
    "T1566",  # Phishing
    "T1078",  # Valid Accounts
    "T1190",  # Exploit Public-Facing Application
    # Execution
    "T1059",  # Command and Scripting Interpreter
    "T1204",  # User Execution
    # Persistence
    "T1136",  # Create Account
    "T1053",  # Scheduled Task/Job
    "T1098",  # Account Manipulation
    # Privilege Escalation
    "T1548",  # Abuse Elevation Control Mechanism
    "T1134",  # Access Token Manipulation
    # Defense Evasion
    "T1562",  # Impair Defenses
    "T1070",  # Indicator Removal
    # Credential Access
    "T1110",  # Brute Force
    "T1003",  # OS Credential Dumping
    "T1558",  # Steal or Forge Kerberos Tickets
    # Lateral Movement
    "T1021",  # Remote Services
    "T1570",  # Lateral Tool Transfer
    # Collection / Exfiltration
    "T1005",  # Data from Local System
    "T1567",  # Exfiltration Over Web Service
    "T1041",  # Exfiltration Over C2 Channel
    # Discovery
    "T1087",  # Account Discovery
    "T1069",  # Permission Groups Discovery
    # Impact
    "T1486",  # Data Encrypted for Impact
    "T1489",  # Service Stop
    # Command and Control
    "T1071",  # Application Layer Protocol
}

_ATTACK_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data"
    "/master/enterprise-attack/enterprise-attack.json"
)

_CACHE_FILENAME = "enterprise-attack.json"
_CACHE_TTL_SECONDS = 86400  # 24 hours


def fetch_mitre_techniques(cache_dir: str | None = None) -> list[dict]:
    """Fetch enterprise ATT&CK techniques, filtered to curated subset.

    If cache_dir is provided, uses a local file cache with 24-hour TTL.
    On any error (network, parse), logs a warning and returns an empty list
    for graceful degradation.

    Returns:
        List of dicts with keys: technique_id, name, description, tactics.
    """
    try:
        stix_json = _load_stix_data(cache_dir)
        return _parse_techniques(stix_json)
    except Exception:
        logger.warning(
            "Failed to fetch MITRE ATT&CK techniques, returning empty list",
            exc_info=True,
        )
        return []


def _load_stix_data(cache_dir: str | None) -> dict:
    """Load STIX JSON from cache or download from GitHub."""
    if cache_dir is not None:
        cache_path = Path(cache_dir) / _CACHE_FILENAME
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < _CACHE_TTL_SECONDS:
                logger.info("Loading MITRE ATT&CK data from cache: %s", cache_path)
                return json.loads(cache_path.read_text(encoding="utf-8"))

    logger.info("Downloading MITRE ATT&CK data from GitHub...")
    response = requests.get(_ATTACK_URL, timeout=60)
    response.raise_for_status()
    stix_json = response.json()

    if cache_dir is not None:
        cache_path = Path(cache_dir) / _CACHE_FILENAME
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(stix_json), encoding="utf-8"
        )
        logger.info("Cached MITRE ATT&CK data to: %s", cache_path)

    return stix_json


def _parse_techniques(stix_json: dict) -> list[dict]:
    """Parse STIX data and filter to curated technique subset."""
    src = MemoryStore(stix_data=stix_json["objects"], allow_custom=True)

    # Get all enterprise techniques (not sub-techniques)
    techniques = src.query([
        Filter("type", "=", "attack-pattern"),
        Filter("x_mitre_is_subtechnique", "=", False),
    ])

    result = []
    for tech in techniques:
        ext_refs = tech.get("external_references", [])
        attack_id = next(
            (
                ref["external_id"]
                for ref in ext_refs
                if ref.get("source_name") == "mitre-attack"
            ),
            None,
        )
        if attack_id and attack_id in CURATED_TECHNIQUE_IDS:
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
