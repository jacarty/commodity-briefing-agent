"""End-to-end smoke test for the Phase 3 orchestrator.

Runs the full pipeline from scratch and prints what happened at
each stage plus the final FinalBrief. This is THE test that
proves Phase 3 works end-to-end.

What this proves:
- The custom BaseAgent orchestrator drives all six stages
- escalate=False suppression works (both loops exit cleanly
  without halting the pipeline)
- output_schema=FinalBrief produces a valid Pydantic structure
- All seven specialists (3 research + synthesise + cross_check +
  draft + sense_check + revise + final_brief) wire together
- Total wall-clock matches the worst-case budget from STEP-07
  (~120-170s with audit revises, less without)

Cost: full pipeline run. Probably ~$0.05-0.10 in Gemini Flash
tokens.

Run with:
    uv run python -m briefing_agent.smoke_orchestrator

Manual inspection:
- Did the pipeline complete without crashing?
- Did both audit loops exit (either via PASS or via cap)?
- Does state['final_brief'] contain a valid FinalBrief dict
  with subject, html_body, plain_text_body?
- Does the HTML body use only <h2>, <p>, <strong> tags?
- Does the plain text body have section headers in UPPERCASE?
"""

import asyncio
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK

from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from briefing_agent.orchestrator import build_orchestrator  # noqa: E402

APP_NAME = "phase3_smoke_orchestrator"
USER_ID = "smoke_user"


async def main() -> None:
    today = date.today().isoformat()
    print(f"Phase 3 full-pipeline smoke test (target date: {today})\n")
    print("=" * 60)
    print("Building orchestrator with all 7 specialists + 2 loops...")
    print("=" * 60)

    orchestrator = build_orchestrator()

    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID)

    runner = Runner(app_name=APP_NAME, agent=orchestrator, session_service=session_service)

    user_message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    f"Run the daily oil briefing pipeline for "
                    f"{today}. Target commodity: crude oil."
                )
            )
        ],
    )

    print()
    print("=" * 60)
    print("RUNNING PIPELINE")
    print("=" * 60)
    print()

    # Track per-agent event counts and exit_loop calls
    event_counts: dict[str, int] = {}
    exit_loop_calls = 0
    start = time.perf_counter()

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session.id,
        new_message=user_message,
    ):
        author = event.author or "?"
        event_counts[author] = event_counts.get(author, 0) + 1

        # Detect exit_loop invocations
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call is not None and part.function_call.name == "exit_loop":
                    exit_loop_calls += 1

        # Print final response from each agent in real time
        if event.is_final_response():
            print(f"  [{author}] (event {event_counts[author]})")

    elapsed = time.perf_counter() - start

    print()
    print("=" * 60)
    print(f"PIPELINE COMPLETE in {elapsed:.1f}s")
    print("=" * 60)
    print()
    print("Event counts by agent:")
    for author, count in event_counts.items():
        print(f"  {author}: {count}")
    print(f"\nTotal exit_loop calls: {exit_loop_calls}")
    print()

    # Read final state
    completed = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session.id
    )

    print("=" * 60)
    print("STATE SUMMARY")
    print("=" * 60)
    for key in (
        "price_data",
        "news_research",
        "catalysts_research",
        "geo_research",
        "synthesis",
        "cross_check_result",
        "draft",
        "sense_check_result",
        "final_brief",
    ):
        value = completed.state.get(key)
        if value is None:
            print(f"  {key}: (missing)")
        elif isinstance(value, dict):
            print(f"  {key}: dict with keys {list(value.keys())}")
        else:
            preview = str(value)[:80].replace("\n", " ")
            print(f"  {key}: {preview}...")

    print()
    print("=" * 60)
    print("FINAL BRIEF")
    print("=" * 60)

    final_brief = completed.state.get("final_brief")
    if final_brief is None:
        print("⚠️  final_brief is missing from state.")
    elif not isinstance(final_brief, dict):
        print(f"⚠️  final_brief is not a dict, got {type(final_brief).__name__}")
        print(f"    Value: {final_brief}")
    else:
        # Validate the FinalBrief structure
        required_keys = {"subject", "html_body", "plain_text_body"}
        missing = required_keys - set(final_brief.keys())
        if missing:
            print(f"⚠️  final_brief is missing fields: {missing}")
        else:
            print(f"\nSubject: {final_brief['subject']}\n")
            print("--- HTML body ---")
            print(final_brief["html_body"])
            print()
            print("--- Plain text body ---")
            print(final_brief["plain_text_body"])

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    success_checks = {
        "Pipeline completed without exception": True,  # we got here
        "Total wall-clock under 200s": elapsed < 200,
        "All expected state keys populated": all(
            completed.state.get(k) is not None
            for k in [
                "price_data",
                "news_research",
                "catalysts_research",
                "geo_research",
                "synthesis",
                "draft",
                "final_brief",
            ]
        ),
        "final_brief is a dict": isinstance(final_brief, dict),
        "final_brief has all required fields": (
            isinstance(final_brief, dict)
            and {"subject", "html_body", "plain_text_body"}.issubset(final_brief)
        ),
        "At least one exit_loop call (loops working)": exit_loop_calls >= 1,
    }
    for check, passed in success_checks.items():
        marker = "✅" if passed else "❌"
        print(f"  {marker} {check}")

    if all(success_checks.values()):
        print("\n✅ Phase 3 end-to-end pipeline validated.")
    else:
        print("\n⚠️  Some checks failed. Inspect output above.")


if __name__ == "__main__":
    asyncio.run(main())
