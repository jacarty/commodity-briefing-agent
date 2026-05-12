"""Dual-scenario smoke test for sense_check.

Runs sense_check twice with the same real synthesis but two
different draft inputs:

1. **PASS scenario** — a real draft produced by running the full
   upstream chain (research + synthesise + draft). Sense_check
   should return VERDICT: PASS and call exit_loop.

2. **FAIL scenario** — a fabricated bad draft with deliberate
   issues:
   - Uses bullet points (forbidden by the draft prompt)
   - Repeats a story across NEWS and GEOPOLITICS sections
   - Introduces a claim not present in the synthesis
   Sense_check should return VERDICT: FAIL and NOT call exit_loop.

This tests:
- Gemini's calibration on PASS-with-notes for the rendering layer
- exit_loop tool invocation pattern (same as cross_check)
- Whether sense_check exhibits the empty-state-on-PASS behaviour
  observed in cross_check (expected: yes)

Cost: parallel research + synthesise + draft + 2 × sense_check.

Run with:
    uv run python -m briefing_agent.smoke_sense_check
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
from briefing_agent.specialists.sense_check import build_sense_check  # noqa: E402
from briefing_agent.specialists.synthesise import build_synthesise  # noqa: E402
from briefing_agent.tools import fetch_price  # noqa: E402
from briefing_agent.workflows.research_parallel import build_research_parallel  # noqa: E402

APP_NAME = "phase3_smoke_sense_check"
USER_ID = "smoke_user"


# Fabricated bad draft. Deliberately constructed to fail audit:
# 1. PRICE SECTION uses bullet points (prose-only rule violated).
# 2. NEWS SECTION and GEOPOLITICS SECTION both lead with the same
#    Strait of Hormuz story (no-section-repetition rule violated).
# 3. CATALYSTS SECTION includes a claim about "OPEC emergency
#    meeting next Tuesday" — fabricated, not in synthesis
#    (faithfulness violation).
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
    """Run the full upstream chain through draft. Returns the session
    id with state populated: price_data, research keys, synthesis,
    draft."""
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
        new_message=types.Content(role="user", parts=[types.Part(text="Produce the synthesis.")]),
    ):
        pass

    draft = build_draft()
    draft_runner = Runner(app_name=APP_NAME, agent=draft, session_service=session_service)
    async for _event in draft_runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="Render the brief.")]),
    ):
        pass

    return session.id


async def run_sense_check(
    session_service: InMemorySessionService,
    session_id: str,
    scenario_label: str,
) -> tuple[str | None, bool]:
    """Invoke sense_check against current session state. Returns the
    sense_check_result text and whether exit_loop was called."""
    sense_check_agent = build_sense_check()
    sc_runner = Runner(app_name=APP_NAME, agent=sense_check_agent, session_service=session_service)

    exit_loop_called = False
    start = time.perf_counter()
    async for event in sc_runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="Audit the draft against the synthesis in state.")],
        ),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call is not None and part.function_call.name == "exit_loop":
                    exit_loop_called = True
    elapsed = time.perf_counter() - start

    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    print(f"      [{scenario_label}] sense_check complete ({elapsed:.1f}s)")
    print(f"      exit_loop called: {exit_loop_called}")
    return completed.state.get("sense_check_result"), exit_loop_called


async def main() -> None:
    print("Dual-scenario smoke test for sense_check\n")

    # ============================================================
    # SCENARIO 1 — PASS path with real draft
    # ============================================================
    print("=" * 60)
    print("SCENARIO 1 — PASS path (real draft from real synthesis)")
    print("=" * 60)

    session_service = InMemorySessionService()

    print("[1/2] gather research + synthesis + draft...")
    session_id = await gather_research_synthesis_and_draft(session_service)

    print("[2/2] sense_check on real draft...")
    result_pass, exit_called_pass = await run_sense_check(session_service, session_id, "PASS")

    print("\nSENSE_CHECK OUTPUT (PASS scenario):")
    print("-" * 60)
    print(
        result_pass
        if result_pass
        else "(empty — expected if Gemini outputs only function_call on PASS)"
    )
    print("-" * 60)
    print()

    # ============================================================
    # SCENARIO 2 — FAIL path with fabricated bad draft
    # ============================================================
    print("=" * 60)
    print("SCENARIO 2 — FAIL path (fabricated bad draft)")
    print("=" * 60)

    # Reuse the synthesis from scenario 1, inject the bad draft.
    src_session = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    fail_session = await session_service.create_session(
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

    print("[1/1] sense_check on fabricated bad draft...")
    result_fail, exit_called_fail = await run_sense_check(session_service, fail_session.id, "FAIL")

    print("\nSENSE_CHECK OUTPUT (FAIL scenario):")
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
    print("  FAIL scenario → exit_loop called = False, output starts with 'VERDICT: FAIL'")
    print()

    fail_starts_correctly = bool(result_fail) and result_fail.startswith("VERDICT: FAIL")

    if exit_called_pass and not exit_called_fail and fail_starts_correctly:
        print("✅ Both scenarios behaved as expected.")
    else:
        print("⚠️  At least one scenario did not behave as expected.")
        print("    Inspect the outputs above for diagnostics.")


if __name__ == "__main__":
    asyncio.run(main())
