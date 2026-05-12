"""Dual-scenario smoke test for the synthesis audit loop.

Tests the full LoopAgent(cross_check, synthesise_revise) under
two scenarios:

1. **Happy path** — real synthesis from real research. Cross_check
   should PASS on iteration 1 and exit the loop immediately.
   Expected: 1 iteration, exit_loop called, state['synthesis']
   unchanged from input.

2. **Fabricated-bad path** — deliberately-broken initial synthesis.
   Cross_check should FAIL on iteration 1. Synthesise_revise runs
   and rewrites state['synthesis']. Cross_check runs again on
   iteration 2 against the revised synthesis. Expected outcome
   is one of:
   - PASS on iteration 2 (best case — revise fixed the issues)
   - FAIL on iteration 2 (hits max_iterations cap)

Either iteration-2 outcome validates loop mechanics. Both prove:
- LoopAgent runs cross_check first per the design
- Synthesise_revise actually runs when cross_check FAILs
- State['synthesis'] is overwritten by revise
- max_iterations=2 caps the loop

What this PR validates that PRs 1 and 2 couldn't:
- exit_loop reliably terminates the loop (STEP-03 open question)
- Gemini's PASS-with-notes calibration (STEP-03 open question)

Cost: one full chain run + one loop run for happy path; one
fabricated-bad loop run.

Run with:
    uv run python -m briefing_agent.smoke_synthesis_loop
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
from briefing_agent.workflows.synthesis_loop import build_synthesis_loop  # noqa: E402

APP_NAME = "phase3_smoke_synthesis_loop"
USER_ID = "smoke_user"


# Same fabricated bad synthesis as smoke_cross_check.py — kept in
# sync via copy-paste. If we need to share it, move to a fixtures
# module later.
FABRICATED_BAD_SYNTHESIS = """\
DOMINANT NARRATIVE
The dominant story today is decelerating Chinese oil demand. China's
EV adoption and economic restructuring have shifted oil consumption
patterns, making demand-side weakness the primary driver. This is
the lens through which today's price action should be read.

PRICE INTERPRETATION
Today's small move higher reflects bearish demand sentiment being
partly offset by short covering. The bullish supply factors are
secondary.

CROSS-STREAM SIGNALS
The most significant signal is the Strait of Hormuz disruption,
which is keeping a structural risk premium in the curve. News and
geopolitics both reinforce that the supply side dominates current
price formation.

RISKS TO VIEW
A genuine surprise drawdown in Chinese inventories would invalidate
the dominant narrative.

HEADLINE METRICS
- WTI spot at $67.50 reflecting structural decline
- China oil demand projected to decline 1.2% in 2026
- Hormuz transit still operating below 50% normal capacity
- US SPR release of 53.3 million barrels announced
- OPEC+ adding 188,000 bpd from June 2026
"""


async def gather_research_and_synthesis(session_service: InMemorySessionService) -> str:
    """Run the full upstream chain. Returns the session id with state
    populated: price_data, news_research, catalysts_research,
    geo_research, synthesis."""
    today = date.today().isoformat()
    price_data = fetch_price()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"price_data": str(price_data)},
    )

    research = build_research_parallel()
    research_runner = Runner(app_name=APP_NAME, agent=research, session_service=session_service)
    async for _event in research_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Target date: {today}. Commodity: crude oil.")],
        ),
    ):
        pass

    synth = build_synthesise()
    synth_runner = Runner(app_name=APP_NAME, agent=synth, session_service=session_service)
    async for _event in synth_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Produce the synthesis.")],
        ),
    ):
        pass

    return session.id


async def run_synthesis_loop(
    session_service: InMemorySessionService,
    session_id: str,
    label: str,
) -> dict:
    """Invoke the synthesis loop and observe iteration behaviour.

    Returns a dict with: iterations_observed, exit_loop_called,
    final_verdict, final_synthesis.
    """
    loop = build_synthesis_loop()
    loop_runner = Runner(app_name=APP_NAME, agent=loop, session_service=session_service)

    cross_check_events = 0
    synthesise_revise_events = 0
    exit_loop_called = False
    start = time.perf_counter()
    async for event in loop_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=f"Run synthesis audit loop ({label}).")],
        ),
    ):
        # Track which sub-agent produced this event
        if event.author == "cross_check" and event.is_final_response():
            cross_check_events += 1
        if event.author == "synthesise_revise" and event.is_final_response():
            synthesise_revise_events += 1

        # Detect exit_loop function call
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call is not None and part.function_call.name == "exit_loop":
                    exit_loop_called = True
    elapsed = time.perf_counter() - start

    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    cc_result = completed.state.get("cross_check_result", "") or ""
    final_verdict = "UNKNOWN"
    if cc_result.startswith("VERDICT: PASS"):
        final_verdict = "PASS"
    elif cc_result.startswith("VERDICT: FAIL"):
        final_verdict = "FAIL"

    print(f"      [{label}] loop complete ({elapsed:.1f}s)")
    print(f"      cross_check responses observed: {cross_check_events}")
    print(f"      synthesise_revise responses observed: {synthesise_revise_events}")
    print(f"      exit_loop called: {exit_loop_called}")
    print(f"      final verdict: {final_verdict}")

    return {
        "cross_check_events": cross_check_events,
        "synthesise_revise_events": synthesise_revise_events,
        "exit_loop_called": exit_loop_called,
        "final_verdict": final_verdict,
        "final_synthesis": completed.state.get("synthesis"),
        "final_cross_check": cc_result,
    }


async def main() -> None:
    print("Dual-scenario smoke test for synthesis_loop\n")

    # ============================================================
    # SCENARIO 1 — Happy path
    # ============================================================
    print("=" * 60)
    print("SCENARIO 1 — Happy path (real synthesis from real research)")
    print("=" * 60)

    session_service = InMemorySessionService()

    print("[1/2] gather research + initial synthesis...")
    session_id = await gather_research_and_synthesis(session_service)

    print("[2/2] run synthesis_loop on real synthesis...")
    happy_result = await run_synthesis_loop(session_service, session_id, "HAPPY")

    print("\nFINAL SYNTHESIS (happy path):")
    print("-" * 60)
    print(happy_result["final_synthesis"])
    print("-" * 60)
    print()

    # ============================================================
    # SCENARIO 2 — Fabricated-bad path
    # ============================================================
    print("=" * 60)
    print("SCENARIO 2 — Fabricated-bad path (deliberately broken synthesis)")
    print("=" * 60)

    price_data = fetch_price()

    # Reuse the research from scenario 1
    src_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    bad_session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={
            "price_data": str(price_data),
            "news_research": src_session.state.get("news_research", ""),
            "catalysts_research": src_session.state.get("catalysts_research", ""),
            "geo_research": src_session.state.get("geo_research", ""),
            "synthesis": FABRICATED_BAD_SYNTHESIS,
        },
    )

    print("[1/1] run synthesis_loop on fabricated bad synthesis...")
    fail_result = await run_synthesis_loop(session_service, bad_session.id, "FAIL→REVISE")

    print("\nFINAL SYNTHESIS (fail→revise path):")
    print("-" * 60)
    print(fail_result["final_synthesis"])
    print("-" * 60)
    print()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Happy path:")
    print(f"  cross_check events: {happy_result['cross_check_events']}")
    print(f"  synthesise_revise events: {happy_result['synthesise_revise_events']}")
    print(f"  exit_loop called: {happy_result['exit_loop_called']}")
    print(f"  final verdict: {happy_result['final_verdict']}")
    print()
    print("Fail→revise path:")
    print(f"  cross_check events: {fail_result['cross_check_events']}")
    print(f"  synthesise_revise events: {fail_result['synthesise_revise_events']}")
    print(f"  exit_loop called: {fail_result['exit_loop_called']}")
    print(f"  final verdict: {fail_result['final_verdict']}")
    print()
    print("Expected for happy path:")
    print("  cross_check=1, synthesise_revise=0, exit_loop=True, verdict=PASS")
    print()
    print("Expected for fail→revise path (either outcome is informative):")
    print("  (best case) cross_check=2, synthesise_revise=1, exit_loop=True, verdict=PASS")
    print("  (cap case)  cross_check=2, synthesise_revise=2, exit_loop=False, verdict=FAIL")


if __name__ == "__main__":
    asyncio.run(main())
