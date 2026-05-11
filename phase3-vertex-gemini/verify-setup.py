"""verify_setup.py — one-shot sanity check for Phase 3.

Confirms that:
- google-adk is installed and importable
- .env loads cleanly and points at the right Vertex project
- ADC credentials work for Vertex AI
- Gemini 2.5 Flash is reachable via the Vertex backend
- The first-party google_search tool is reachable and returns
  search-grounded text

If this script exits with `✅`, Phase 3's environment is good
and we can move to STEP-03 design. If it errors, the error
message should be enough to diagnose — usually one of:

- `.env` missing or values wrong → fix and retry
- ADC expired → re-run `gcloud auth application-default login`
- Vertex AI API not enabled → run
  `gcloud services enable aiplatform.googleapis.com`
- Quota / model access issue → check Vertex AI console
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load .env BEFORE importing ADK — ADK / google-genai check the
# GOOGLE_GENAI_USE_VERTEXAI env var at import / client-construction
# time, so the env has to be in place first.
load_dotenv()


def assert_env() -> None:
    """Fail fast if required env vars are missing."""
    required = [
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_VERTEXAI",
    ]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Missing required env vars: {', '.join(missing)}")
        print("   Did you copy env-example.txt to .env?")
        sys.exit(1)

    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() != "true":
        print("❌ GOOGLE_GENAI_USE_VERTEXAI must be 'True' (we're using the Vertex backend).")
        sys.exit(1)


async def run_verify() -> None:
    """Build a minimal ADK agent, invoke it, print the result."""
    # Imports inside the function so the env check runs first and
    # any import-time errors point at the right cause.
    from google.adk.agents import Agent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import google_search
    from google.genai import types

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    print(f"Project:  {project}")
    print(f"Location: {location}")
    print("Model:    gemini-2.5-flash")
    print()

    # Minimal agent: Flash + google_search, nothing else.
    agent = Agent(
        name="verify_agent",
        model="gemini-2.5-flash",
        description="Sanity-check agent that uses Google Search to answer a basic question.",
        instruction=(
            "You are a helpful assistant. Use the google_search tool to "
            "answer the user's question with current information. Keep "
            "your response to one or two sentences."
        ),
        tools=[google_search],
    )

    # In-memory session service is fine for a one-shot check. Phase 3's
    # eventual orchestrator may use the same; or may use Agent Engine
    # Sessions — STEP-03 decision.
    app_name = "phase3_verify"
    user_id = "verify_user"
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
    )

    runner = Runner(
        app_name=app_name,
        agent=agent,
        session_service=session_service,
    )

    query = "What is the current price of WTI crude oil per barrel?"
    print(f"Query: {query}\n")

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    final_response: str | None = None
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    if not final_response:
        print("❌ Agent did not produce a final response.")
        sys.exit(1)

    print("Response from agent:")
    print(final_response)
    print()
    print("✅ ADK + Vertex + Gemini 2.5 Flash + google_search all working.")


def main() -> None:
    assert_env()
    try:
        asyncio.run(run_verify())
    except Exception as exc:  # noqa: BLE001 — surface the error to the user
        print(f"❌ Verification failed: {type(exc).__name__}: {exc}")
        print()
        print("Common causes:")
        print("- ADC credentials expired → gcloud auth application-default login")
        print("- Vertex AI API not enabled → gcloud services enable aiplatform.googleapis.com")
        print("- Wrong project / region in .env")
        print("- Network or permission issue")
        sys.exit(1)


if __name__ == "__main__":
    main()
