"""Smoke test for the deployed orchestrator.

Connects to the deployed Agent Engine resource and runs a single
pipeline invocation. Comparable to smoke_orchestrator but hits the
managed service rather than running locally.

What this proves:
- Deployment is reachable
- Managed sessions work
- The full pipeline runs identically on Agent Engine
- Latency is comparable to local (or better, given Vertex
  co-location with Gemini)

Pre-requisites:

- Run `uv run python -m briefing_agent.deploy` first
- Copy the printed resource name into .env as
  DEPLOYED_AGENT_RESOURCE

Run with:

    uv run python -m briefing_agent.smoke_deployed_orchestrator
"""

import asyncio
import os
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()

import vertexai  # noqa: E402
from vertexai import agent_engines  # noqa: E402


async def main() -> None:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ["GOOGLE_CLOUD_LOCATION"]
    resource = os.environ.get("DEPLOYED_AGENT_RESOURCE")

    if not resource:
        print("❌ DEPLOYED_AGENT_RESOURCE not set in .env")
        print("   Run the deploy script first and add the resource name.")
        return

    vertexai.init(project=project, location=location)

    print(f"Connecting to deployed agent: {resource}")
    remote_app = agent_engines.get(resource_name=resource)

    today = date.today().isoformat()
    print(f"Target date: {today}")
    print()

    # Create a managed session
    session = await remote_app.async_create_session(user_id="smoke_user")
    session_id = session.get("id") if isinstance(session, dict) else session.id
    print(f"Session created: {session_id}")
    print()

    print("=" * 60)
    print("RUNNING DEPLOYED PIPELINE")
    print("=" * 60)
    print()

    event_count = 0
    start = time.perf_counter()
    async for event in remote_app.async_stream_query(
        user_id="smoke_user",
        session_id=session_id,
        message=(
            f"Run the daily oil briefing pipeline for {today}. " f"Target commodity: crude oil."
        ),
    ):
        event_count += 1
        author = event.get("author", "?") if isinstance(event, dict) else "?"
        print(f"  event {event_count} [{author}]")
    elapsed = time.perf_counter() - start

    print()
    print("=" * 60)
    print(f"DEPLOYED PIPELINE COMPLETE in {elapsed:.1f}s ({event_count} events)")
    print("=" * 60)
    print()

    # Read final state from managed session
    final_session = await remote_app.async_get_session(user_id="smoke_user", session_id=session_id)
    state = (
        final_session.get("state", {}) if isinstance(final_session, dict) else final_session.state
    )
    final_brief = state.get("final_brief")

    print("FINAL BRIEF (from deployed agent):")
    if final_brief is None:
        print("⚠️  final_brief is missing from session state")
    elif isinstance(final_brief, dict):
        print(f"\nSubject: {final_brief.get('subject')}\n")
        print("--- HTML body ---")
        print(final_brief.get("html_body", "(missing)"))
        print()
        print("--- Plain text body ---")
        print(final_brief.get("plain_text_body", "(missing)"))
    else:
        print(f"Unexpected type: {type(final_brief).__name__}")
        print(final_brief)


if __name__ == "__main__":
    asyncio.run(main())
