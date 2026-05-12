"""Dual-scenario smoke test for cross_check.

Runs cross_check twice with the same real research but two
different synthesis inputs:

1. **PASS scenario** — a real synthesis produced by running the
   full upstream chain (research + synthesise). Cross_check
   should return VERDICT: PASS and call exit_loop.

2. **FAIL scenario** — a fabricated synthesis with deliberate
   issues:
   - DOMINANT NARRATIVE claims one story, CROSS-STREAM SIGNALS
     identify a different one (consistency issue)
   - HEADLINE METRICS include a fabricated price that doesn't
     match price_data (grounding issue)
   Cross_check should return VERDICT: FAIL and NOT call exit_loop.

This tests:
- Gemini's calibration on PASS-with-notes (bias toward passing)
- Gemini's willingness to FAIL when issues are material
- exit_loop tool invocation on PASS verdict
- Whether the exit_loop signal actually appears in the event
  stream (the function_call event we'd observe)

Cost: parallel research + synthesise + 2 × cross_check calls.

Run with:
    uv run python -m briefing_agent.smoke_cross_check
"""

import asyncio
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from briefing_agent.specialists.cross_check import build_cross_check  # noqa: E402
from briefing_agent.specialists.synthesise import build_synthesise  # noqa: E402
from briefing_agent.tools import fetch_price  # noqa: E402
from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_cross_check"
USER_ID = "smoke_user"


# Fabricated bad synthesis. Deliberately constructed to fail audit:
# 1. DOMINANT NARRATIVE claims "China demand" is the lead.
# 2. CROSS-STREAM SIGNALS identifies "Hormuz disruption" as the lead.
#    These contradict — consistency issue.
# 3. HEADLINE METRICS includes "$67.50 spot" which won't match the
#    real price_data the cross_check sees — grounding issue.
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


async def run_cross_check(
    session_service: InMemorySessionService,
    session_id: str,
    scenario_label: str,
) -> tuple[str | None, bool]:
    """Invoke cross_check against the current session state. Returns
    the cross_check_result text and whether exit_loop was called."""
    cross_check_agent = build_cross_check()
    cc_runner = Runner(
        app_name=APP_NAME,
        agent=cross_check_agent,
        session_service=session_service,
    )

    exit_loop_called = False
    start = time.perf_counter()
    async for event in cc_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Audit the synthesis in state.")],
        ),
    ):
        # Detect exit_loop function call in the event stream
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call is not None and part.function_call.name == "exit_loop":
                    exit_loop_called = True
    elapsed = time.perf_counter() - start

    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    print(f"      [{scenario_label}] cross_check complete ({elapsed:.1f}s)")
    print(f"      exit_loop called: {exit_loop_called}")
    return completed.state.get("cross_check_result"), exit_loop_called


async def main() -> None:
    print("Dual-scenario smoke test for cross_check\n")

    # ============================================================
    # SCENARIO 1 — PASS path with real synthesis
    # ============================================================
    print("=" * 60)
    print("SCENARIO 1 — PASS path (real synthesis from real research)")
    print("=" * 60)

    session_service = InMemorySessionService()

    print("[1/2] gather research + synthesis...")
    session_id = await gather_research_and_synthesis(session_service)

    print("[2/2] cross_check on real synthesis...")
    result_pass, exit_called_pass = await run_cross_check(session_service, session_id, "PASS")

    print("\nCROSS_CHECK OUTPUT (PASS scenario):")
    print("-" * 60)
    print(result_pass)
    print("-" * 60)
    print()

    # ============================================================
    # SCENARIO 2 — FAIL path with fabricated bad synthesis
    # ============================================================
    print("=" * 60)
    print("SCENARIO 2 — FAIL path (fabricated bad synthesis)")
    print("=" * 60)

    # Reuse the same research from scenario 1, just inject the bad
    # synthesis. New session needed (cross_check would otherwise
    # see the prior cross_check_result; we want a clean run).
    price_data = fetch_price()

    # Pull research from scenario 1's session and copy it into a
    # fresh session along with the fabricated synthesis.
    src_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    fail_session = await session_service.create_session(
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

    print("[1/1] cross_check on fabricated bad synthesis...")
    result_fail, exit_called_fail = await run_cross_check(session_service, fail_session.id, "FAIL")

    print("\nCROSS_CHECK OUTPUT (FAIL scenario):")
    print("-" * 60)
    print(result_fail)
    print("-" * 60)
    print()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"PASS scenario: exit_loop called = {exit_called_pass}")
    print(f"FAIL scenario: exit_loop called = {exit_called_fail}")
    print()
    print("Expected:")
    print("  PASS scenario → exit_loop called = True")
    print("  FAIL scenario → exit_loop called = False")
    print()

    if (
        exit_called_pass
        and not exit_called_fail
        and result_pass
        and result_pass.startswith("VERDICT: PASS")
        and result_fail
        and result_fail.startswith("VERDICT: FAIL")
    ):
        print("✅ Both scenarios behaved as expected.")
    else:
        print("⚠️  At least one scenario did not behave as expected.")
        print("    Inspect the outputs above for diagnostics.")


if __name__ == "__main__":
    asyncio.run(main())
