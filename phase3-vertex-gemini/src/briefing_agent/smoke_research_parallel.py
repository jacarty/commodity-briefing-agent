"""Manual smoke test for the parallel research stage.

Invokes the ParallelAgent (news + catalysts + geo) concurrently and
prints all three outputs. Unlike per-specialist smokes, this one
does NOT use the run_specialist helper — ParallelAgent doesn't
produce a single "final response", so we inspect session.state
directly after the run completes.

What this proves:
- ParallelAgent runs all three sub-agents concurrently
- Each sub-agent writes to its own output_key in session.state
- No race conditions between the three specialists (distinct keys)
- The full parallel research stage produces the three text blocks
  the orchestrator (PR 5) will consume

Run with:
    uv run python -m briefing_agent.smoke_research_parallel

Manual inspection — three output blocks should appear, one per
specialist, each in its expected format (ITEM / EVENT / THEME).
Total wall-clock time should be roughly that of the slowest
single specialist (since they run in parallel), not the sum.
"""

import asyncio
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK; google-genai checks env at import

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_parallel"
USER_ID = "smoke_user"


async def main() -> None:
    today = date.today().isoformat()
    print("Building research_parallel workflow (3 sub-agents)\n")

    agent = build_research_parallel()

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Conduct full research across news, catalysts, and geopolitics."
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text=instruction)],
    )

    print(f"Invoking with: {instruction!r}\n")
    print("=" * 60)
    print("Event stream (events from sub-agents may interleave):")
    print("=" * 60)

    start = time.perf_counter()
    event_count = 0
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=user_message,
    ):
        event_count += 1
        # Just log which agent the event came from; full content lives in
        # state by the time the run ends.
        print(f"[{event.author or '?'}] event #{event_count}")
    elapsed = time.perf_counter() - start

    print()
    print(f"Run complete in {elapsed:.1f}s ({event_count} events total)\n")

    # Read state from the completed session
    completed = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session.id,
    )

    for key in ("news_research", "catalysts_research", "geo_research"):
        print("=" * 60)
        print(f"state[{key!r}]:")
        print("=" * 60)
        value = completed.state.get(key)
        if value is None:
            print(f"  (missing — sub-agent did not write to {key!r})")
        else:
            print(value)
        print()


if __name__ == "__main__":
    asyncio.run(main())
