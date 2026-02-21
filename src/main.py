"""CLI chat loop entry point for the Sentinel chatbot.

Provides run_chat() which starts an interactive chat session, handling
user input, commands (/clear, /quit, /exit), and error recovery.
Initializes the knowledge base (VectorStore) with seed data, live
Sentinel incidents, playbooks, and MITRE ATT&CK technique data.
"""

import os
import sys

import openai

from src.config import load_settings, validate_env_vars
from src.openai_client import ChatSession
from src.sentinel_client import SentinelClient

_WELCOME_BANNER = """\
Sentinel AI Assistant
Query incidents, alerts, trends, and entities using natural language.
Ask about historical incidents, playbooks, or MITRE ATT&CK techniques.
Commands: /clear (reset conversation), /quit or /exit (leave)
"""

_GOODBYE = "Goodbye."


def _init_knowledge_base(settings, sentinel_client):
    """Initialize VectorStore and ingest seed data, live incidents, playbooks, and MITRE data.

    Returns VectorStore instance or None on failure (graceful degradation).
    """
    # Import KB dependencies
    from src.knowledge.playbooks import PLAYBOOKS, build_playbook_chunks
    from src.knowledge.seed_incidents import (
        SEED_INCIDENTS,
        build_incident_document,
        build_incident_metadata,
    )
    from src.mitre import fetch_mitre_techniques
    from src.vector_store import VectorStore

    # Create VectorStore
    try:
        vector_store = VectorStore(settings)
    except Exception as exc:
        print(
            f"Warning: Knowledge base unavailable ({exc})",
            file=sys.stderr,
        )
        return None

    # Seed data ingestion
    incident_docs = [
        {
            "id": inc["id"],
            "document": build_incident_document(inc),
            "metadata": build_incident_metadata(inc),
        }
        for inc in SEED_INCIDENTS
    ]
    vector_store.upsert_incidents(incident_docs)

    # Playbook ingestion
    playbook_chunks = [
        chunk for pb in PLAYBOOKS for chunk in build_playbook_chunks(pb)
    ]
    vector_store.upsert_playbooks(playbook_chunks)

    # Live Sentinel incident ingestion
    try:
        live_result = sentinel_client.query_incidents(
            time_window="last_30d",
            min_severity="Informational",
            limit=100,
        )
        # Only process if it's a successful QueryResult (has .results attr)
        if hasattr(live_result, "results"):
            live_docs = []
            for inc in live_result.results:
                live_docs.append({
                    "id": f"incident-{inc.number}",
                    "document": build_incident_document({
                        "title": inc.title,
                        "severity": inc.severity,
                        "status": inc.status,
                        "description": inc.description,
                    }),
                    "metadata": {
                        "incident_number": inc.number,
                        "title": inc.title,
                        "severity": inc.severity,
                        "status": inc.status,
                        "source": "sentinel",
                        "mitre_techniques": "",
                        "created_date": inc.created_time.strftime(
                            "%Y-%m-%d"
                        ),
                    },
                })
            if live_docs:
                vector_store.upsert_incidents(live_docs)
    except Exception as exc:
        print(
            f"Warning: Could not ingest live incidents ({exc})",
            file=sys.stderr,
        )

    # MITRE ATT&CK data fetch (enrichment context)
    try:
        cache_dir = os.path.join(settings.chromadb_path, "mitre_cache")
        os.makedirs(cache_dir, exist_ok=True)
        techniques = fetch_mitre_techniques(cache_dir=cache_dir)
        print(
            f"MITRE ATT&CK: {len(techniques)} techniques loaded",
            file=sys.stderr,
        )
    except Exception as exc:
        print(
            f"Warning: Could not fetch MITRE ATT&CK data ({exc})",
            file=sys.stderr,
        )

    # Print startup summary
    counts = vector_store.get_collection_counts()
    print(
        f"Knowledge base loaded: {counts['incidents']} incidents, "
        f"{counts['playbooks']} playbooks",
        file=sys.stderr,
    )

    return vector_store


def run_chat() -> None:
    """Main CLI chat loop. Entry point for the chatbot."""
    # Validate environment
    _passed, failed = validate_env_vars()
    if failed:
        print(
            f"Configuration error: {len(failed)} required env var(s) missing:",
            file=sys.stderr,
        )
        for var_desc in failed:
            print(f"  - {var_desc}", file=sys.stderr)
        sys.exit(1)

    settings = load_settings()
    sentinel_client = SentinelClient(settings)

    # Initialize knowledge base (graceful degradation on failure)
    vector_store = _init_knowledge_base(settings, sentinel_client)
    if vector_store is None:
        print(
            "Knowledge base unavailable -- running with Sentinel tools only.",
            file=sys.stderr,
        )

    session = ChatSession(
        settings,
        sentinel_client=sentinel_client,
        vector_store=vector_store,
    )

    print(_WELCOME_BANNER, file=sys.stderr)

    while True:
        try:
            user_input = input("\nYou: ")
        except KeyboardInterrupt:
            print(f"\n{_GOODBYE}")
            break
        except EOFError:
            print(f"\n{_GOODBYE}")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit"):
            print(_GOODBYE)
            break

        if user_input.lower() == "/clear":
            summary = session.clear()
            # Clear terminal: ANSI escape \033[2J clears screen, \033[H moves cursor home
            print("\033[2J\033[H", end="", flush=True)
            print(_WELCOME_BANNER, file=sys.stderr)
            print("")
            print(
                "-------------- Conversation cleared --------------"
            )
            print("")
            print("Summary of previous conversation:")
            print(f"{summary}")
            print("")
            print(
                "--------------------------------------------------"
            )
            print("")
            continue

        try:
            response = session.send_message(user_input)
            print(f"\nAssistant: {response}")
        except openai.AuthenticationError:
            print(
                "\nError: Authentication failed. Check your API key.",
                file=sys.stderr,
            )
        except openai.APIConnectionError:
            print(
                "\nError: Could not connect to Azure OpenAI. Check your endpoint.",
                file=sys.stderr,
            )
        except openai.APIError as e:
            print(
                f"\nError: Azure OpenAI API error: {e.message}",
                file=sys.stderr,
            )
