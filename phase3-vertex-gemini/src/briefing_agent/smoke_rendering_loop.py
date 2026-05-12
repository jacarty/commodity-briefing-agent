"""Dual-scenario smoke test for the rendering audit loop.

Tests the full LoopAgent(sense_check, revise) under two scenarios:

1. **Happy path** — real draft from real synthesis. Sense_check
   should PASS on iteration 1 and exit the loop immediately.
   Expected: 1 iteration, exit_loop called, state['draft']
   unchanged from input.

2. **Fabricated-bad path** — deliberately-broken initial draft
   (bullet points, story repetition, fabricated catalyst).
   Sense_check should FAIL on iteration 1. Revise runs and
   produces a corrected draft. Sense_check runs again on
   iteration 2 against the revised draft. Expected outcome is
   either:
   - PASS on iteration 2 (best case — revise fixed the issues)
   - FAIL on iteration 2 (hits max_iterations cap)

Either iteration-2 outcome validates loop mechanics.

In addition: this is the first test of revise's central
behavioural promise — **targeted revision, not full rewrite**.
Inspect the iteration-2 draft to see whether revise:
- Preserved sections that weren't flagged
- Only rewrote the parts the audit called out
- Maintained voice and structure

The synthesis_loop in PR 3 didn't have an equivalent question
because synthesise_revise was a full re-synthesis. Revise is
different: the test is preservation, not rewriting.

What this PR validates that PR 3 couldn't:
- Whether revise stays surgical or full-rewrites the draft
  (key behavioural finding, deferred from STEP-03's "what I'm
  not yet sure about")

Cost: one full chain run + one loop run for happy path; one
fabricated-bad loop run.

Run with:
    uv run python -m briefing_agent.smoke_rendering_loop
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
from briefing_agent.workflows.rendering_loop import build_rendering_loop  # noqa: E402
from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_rendering_loop"
USER_ID = "smoke_user"


# Same fabricated bad draft as smoke_sense_check.py — kept in sync
# via copy-paste. If we need to share these fixtures, move to a
# fixtures module later.
FABRICATED_BAD_DRAFT = """\
PRICE SECTION
Crude prices moved higher today. Key facts about the session:
- Last close: above $100/bbl
- Daily change: positive
- Intraday range: wide

The move reflects a market reacting to ongoing supply concerns.

NEWS SECTION
The dominant news story today is the continued disruption to the
Strait of Hormuz, which remains effectively closed. This single
factor is driving everything else in the market. US-Iran tensions
remain at the heart of the situation, with no near-term resolution
in sight. The Strategic Petroleum Reserve release announced earlier
this week is being seen as a temporary palliative rather than a
structural fix.

CATALYSTS SECTION
The OPEC+ group is reportedly preparing an emergency meeting next
Tuesday to discuss possible production increases in response to
the supply shock. US CPI data is also due, which could move the
dollar and affect oil pricing on a derivative basis.

GEOPOLITICS SECTION
The Strait of Hormuz disruption is the structural backdrop for
everything else in the oil market. Even if peace talks resumed
tomorrow, the operational disruption to tanker traffic would take
weeks to fully reverse. This is the story of the year for
commodity markets.
"""


async def gather_research_synthesis_and_draft(
    session_service: InMemorySessionService,
) -> str:
    """Run the full upstream chain through draft. Returns session id
    with state populated."""
    today = date.today().isoformat()
    price_data = fetch_price()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"price_data": str(price_data)},
    )

    research = build_research_parallel()
    rr = Runner(app_name=APP_NAME, agent=research, session_service=session_service)
    async for _e in rr.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Target date: {today}. Commodity: crude oil.")],
        ),
    ):
        pass

    synth = build_synthesise()
    sr = Runner(app_name=APP_NAME, agent=synth, session_service=session_service)
    async for _e in sr.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="Produce the synthesis.")]),
    ):
        pass

    draft = build_draft()
    dr = Runner(app_name=APP_NAME, agent=draft, session_service=session_service)
    async for _e in dr.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="Render the brief.")]),
    ):
        pass

    return session.id


async def run_rendering_loop(
    session_service: InMemorySessionService,
    session_id: str,
    label: str,
) -> dict:
    """Invoke the rendering loop and observe iteration behaviour.

    Returns dict with: sense_check_events, revise_events,
    exit_loop_called, final_draft.
    """
    loop = build_rendering_loop()
    loop_runner = Runner(app_name=APP_NAME, agent=loop, session_service=session_service)

    sense_check_events = 0
    revise_events = 0
    exit_loop_called = False
    start = time.perf_counter()
    async for event in loop_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Run rendering audit loop ({label}).")],
        ),
    ):
        if event.author == "sense_check" and event.is_final_response():
            sense_check_events += 1
        if event.author == "revise" and event.is_final_response():
            revise_events += 1

        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call is not None and part.function_call.name == "exit_loop":
                    exit_loop_called = True
    elapsed = time.perf_counter() - start

    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )

    print(f"      [{label}] loop complete ({elapsed:.1f}s)")
    print(f"      sense_check responses observed: {sense_check_events}")
    print(f"      revise responses observed: {revise_events}")
    print(f"      exit_loop called: {exit_loop_called}")

    return {
        "sense_check_events": sense_check_events,
        "revise_events": revise_events,
        "exit_loop_called": exit_loop_called,
        "final_draft": completed.state.get("draft"),
    }


async def main() -> None:
    print("Dual-scenario smoke test for rendering_loop\n")

    # ============================================================
    # SCENARIO 1 — Happy path
    # ============================================================
    print("=" * 60)
    print("SCENARIO 1 — Happy path (real draft from real synthesis)")
    print("=" * 60)

    session_service = InMemorySessionService()

    print("[1/2] gather research + synthesis + initial draft...")
    session_id = await gather_research_synthesis_and_draft(session_service)

    print("[2/2] run rendering_loop on real draft...")
    happy = await run_rendering_loop(session_service, session_id, "HAPPY")

    print("\nFINAL DRAFT (happy path):")
    print("-" * 60)
    print(happy["final_draft"])
    print("-" * 60)
    print()

    # ============================================================
    # SCENARIO 2 — Fabricated-bad path
    # ============================================================
    print("=" * 60)
    print("SCENARIO 2 — Fabricated-bad path (deliberately broken draft)")
    print("=" * 60)

    src_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    bad_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "price_data": src_session.state.get("price_data", ""),
            "news_research": src_session.state.get("news_research", ""),
            "catalysts_research": src_session.state.get("catalysts_research", ""),
            "geo_research": src_session.state.get("geo_research", ""),
            "synthesis": src_session.state.get("synthesis", ""),
            "draft": FABRICATED_BAD_DRAFT,
        },
    )

    print("[1/1] run rendering_loop on fabricated bad draft...")
    fail = await run_rendering_loop(session_service, bad_session.id, "FAIL→REVISE")

    print("\nFINAL DRAFT (fail→revise path):")
    print("-" * 60)
    print(fail["final_draft"])
    print("-" * 60)
    print()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Happy path:")
    print(f"  sense_check events: {happy['sense_check_events']}")
    print(f"  revise events: {happy['revise_events']}")
    print(f"  exit_loop called: {happy['exit_loop_called']}")
    print()
    print("Fail→revise path:")
    print(f"  sense_check events: {fail['sense_check_events']}")
    print(f"  revise events: {fail['revise_events']}")
    print(f"  exit_loop called: {fail['exit_loop_called']}")
    print()
    print("Expected for happy path:")
    print("  sense_check=1, revise=0, exit_loop=True")
    print()
    print("Expected for fail→revise path (either outcome is informative):")
    print("  (best case) sense_check=2, revise=1, exit_loop=True")
    print("  (cap case)  sense_check=2, revise=2, exit_loop=False")
    print()
    print("Compare FAIL→REVISE final draft with the fabricated input:")
    print("  - Did revise preserve sections that weren't flagged?")
    print("  - Did revise fix the bullet points in PRICE SECTION?")
    print("  - Did revise remove the fabricated OPEC emergency meeting?")
    print("  - Did revise differentiate NEWS and GEOPOLITICS leads?")


if __name__ == "__main__":
    asyncio.run(main())
