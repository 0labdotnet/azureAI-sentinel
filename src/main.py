"""CLI chat loop entry point for the Sentinel chatbot.

Provides run_chat() which starts an interactive chat session, handling
user input, commands (/clear, /quit, /exit), and error recovery.
"""

import sys

import openai

from src.config import load_settings, validate_env_vars
from src.openai_client import ChatSession
from src.sentinel_client import SentinelClient

_WELCOME_BANNER = """\
Sentinel AI Assistant
Query incidents, alerts, trends, and entities using natural language.
Commands: /clear (reset conversation), /quit or /exit (leave)
"""

_GOODBYE = "Goodbye."


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
    session = ChatSession(settings, sentinel_client=sentinel_client)

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
            print("---------------------------------- Conversation cleared----------------------------------")
            print("")
            print("Summary of previous conversation:")
            print(f"{summary}")
            print("")
            print("-----------------------------------------------------------------------------------------")
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
