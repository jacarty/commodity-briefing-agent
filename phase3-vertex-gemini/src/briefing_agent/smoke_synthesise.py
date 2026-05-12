"""Live-chain smoke test for synthesise.

Runs the full upstream chain — fetch_price + parallel research —
then invokes synthesise, which reads everything from session.state
via template substitution.

Unlike Phase 2's smoke (which concatenated research into a single
input string), Phase 3 lets ADK's state-and-template machinery do
the assembly. Each upstream agent writes to its output_key;
synthesise's instruction has {price_data}, {news_research},
{catalysts_research}, {geo_research} placeholders that ADK fills
in from state before sending to the model.

This is the first test that:
- The full research → synthesise wiring works end-to-end via state
- Synthesise's instruction template substitution resolves all four
  keys correctly
- Gemini produces a five-section synthesis given real research

Cost: parallel research call (3 specialists) + synthesise call.
Single-digit cents per run.

Run with:
    uv run python -m briefing_agent.smoke_synthesise

Manual inspection — does the synthesis have all five section
headers in the right order? Does CROSS-STREAM SIGNALS actually
reference inter-stream patterns? Are HEADLINE METRICS specific
and grounded in the research?
"""

import asyncio
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from briefing_agent.specialists.synthesise import build_synthesise  # noqa: E402
from briefing_agent.tools import fetch_price  # noqa: E402
from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_synthesise"
USER_ID = "smoke_user"


async def main() -> None:
    today = date.today().isoformat()
    print(f"Live-chain smoke test for synthesise (target date: {today})\n")

    session_service = InMemorySessionService()

    # Pre-populate state with the price snapshot. fetch_price is
    # synchronous and the orchestrator will eventually do this
    # directly; the smoke does the same.
    print("[1/3] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}\n")

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"price_data": str(price_data)},
    )

    # Step 2: parallel research. Each sub-agent writes its output_key
    # to state. After this completes, state has price_data,
    # news_research, catalysts_research, geo_research.
    print("[2/3] parallel research...")
    research_agent = build_research_parallel()
    research_runner = Runner(
        app_name=APP_NAME,
        agent=research_agent,
        session_service=session_service,
    )
    research_message = types.Content(
        role="user",
        parts=[types.Part(text=f"Target date: {today}. Commodity: crude oil.")],
    )
    start = time.perf_counter()
    async for _event in research_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=research_message,
    ):
        pass
    print(f"      Parallel research complete ({time.perf_counter() - start:.1f}s)\n")

    # Step 3: synthesise. Reads everything from state via template
    # substitution.
    print("[3/3] synthesise...")
    synthesise_agent = build_synthesise()
    synth_runner = Runner(
        app_name=APP_NAME,
        agent=synthesise_agent,
        session_service=session_service,
    )
    synth_message = types.Content(
        role="user",
        parts=[types.Part(text="Produce the synthesis using the research in state.")],
    )
    start = time.perf_counter()
    async for _event in synth_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=synth_message,
    ):
        pass
    print(f"      Synthesise complete ({time.perf_counter() - start:.1f}s)\n")

    # Read the final synthesis from state
    completed = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session.id,
    )

    print("=" * 60)
    print("SYNTHESIS OUTPUT")
    print("=" * 60)
    print(completed.state.get("synthesis", "(missing — synthesise did not write output_key)"))
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
