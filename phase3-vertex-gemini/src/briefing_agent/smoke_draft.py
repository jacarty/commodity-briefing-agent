"""Live-chain smoke test for draft.

Runs the full upstream chain — fetch_price + parallel research +
initial synthesise — then invokes draft, which reads the synthesis
from session.state and produces a 4-section briefing.

This is the first test that:
- The synthesise → draft wiring works via state
- Gemini produces a four-section brief given a real synthesis
- The draft's instruction template substitution resolves
  {synthesis} correctly

Cost: parallel research call (3 specialists) + synthesise + draft.
Single-digit cents per run.

Run with:
    uv run python -m briefing_agent.smoke_draft

Manual inspection — does the brief have all four section headers
in the right order (PRICE / NEWS / CATALYSTS / GEOPOLITICS)? Is
each section 2-4 paragraphs? Are bullet points absent? Do HEADLINE
METRICS from the synthesis appear naturally in the prose?
"""

import asyncio
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from briefing_agent.specialists.draft import build_draft  # noqa: E402
from briefing_agent.specialists.synthesise import build_synthesise  # noqa: E402
from briefing_agent.tools import fetch_price  # noqa: E402
from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_draft"
USER_ID = "smoke_user"


async def main() -> None:
    today = date.today().isoformat()
    print(f"Live-chain smoke test for draft (target date: {today})\n")

    session_service = InMemorySessionService()

    print("[1/4] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}\n")

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"price_data": str(price_data)},
    )

    # Step 2: parallel research
    print("[2/4] parallel research...")
    research_agent = build_research_parallel()
    research_runner = Runner(
        app_name=APP_NAME, agent=research_agent, session_service=session_service
    )
    start = time.perf_counter()
    async for _event in research_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Target date: {today}. Commodity: crude oil.")],
        ),
    ):
        pass
    print(f"      Parallel research complete ({time.perf_counter() - start:.1f}s)\n")

    # Step 3: synthesise
    print("[3/4] synthesise...")
    synthesise_agent = build_synthesise()
    synth_runner = Runner(
        app_name=APP_NAME, agent=synthesise_agent, session_service=session_service
    )
    start = time.perf_counter()
    async for _event in synth_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Produce the synthesis.")],
        ),
    ):
        pass
    print(f"      Synthesise complete ({time.perf_counter() - start:.1f}s)\n")

    # Step 4: draft
    print("[4/4] draft...")
    draft_agent = build_draft()
    draft_runner = Runner(app_name=APP_NAME, agent=draft_agent, session_service=session_service)
    start = time.perf_counter()
    async for _event in draft_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Render the synthesis into the brief.")],
        ),
    ):
        pass
    print(f"      Draft complete ({time.perf_counter() - start:.1f}s)\n")

    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session.id
    )

    print("=" * 60)
    print("DRAFT OUTPUT")
    print("=" * 60)
    print(completed.state.get("draft", "(missing — draft did not write output_key)"))
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
