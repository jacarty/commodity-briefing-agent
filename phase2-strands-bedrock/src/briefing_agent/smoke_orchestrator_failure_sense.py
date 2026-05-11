"""Failure-path smoke test for the orchestrator's sense_check retry loop.

Mirror of smoke_orchestrator_failure.py but stubs sense_check
instead of cross_check. Tests retry-cap enforcement on the
second of the two retry loops.

Approach is identical to the cross_check failure test:

1. Build a stub `sense_check` specialist that ALWAYS returns
   `VERDICT: FAIL` with realistic FAIL output (REVISION NOTES,
   issue categories).
2. Build a custom orchestrator with the stub in place of real
   sense_check. All other specialists are real.
3. Invoke the orchestrator on a normal briefing request.
4. Count how many times the orchestrator calls sense_check.
5. Pass criterion: sense_check is called exactly 2 times, then
   the orchestrator proceeds to Phase 3 anyway.

What this validates:

- Does the orchestrator stop at the cap (max 2 sense_check
  cycles)?
- Does it correctly proceed to Phase 3 with the latest revised
  draft when the cap is hit?
- Does it produce a FinalBrief at the end even though sense_check
  never passed?

The cross_check failure test (smoke_orchestrator_failure.py)
already validated the prompt-only retry-cap mechanism. This test
extends the validation to the second retry loop. Same mechanism,
different stage.

Cost: roughly 15-20 cents per run. Cheaper than the cross_check
failure test because revise is cheaper than re-research.

Run with:
    uv run python -m briefing_agent.smoke_orchestrator_failure_sense
"""

import os
from datetime import date

from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel
from strands.types.exceptions import StructuredOutputException

from briefing_agent.final_brief import FinalBrief
from briefing_agent.prompts import load_prompt
from briefing_agent.specialists.cross_check import build_cross_check
from briefing_agent.specialists.draft import build_draft
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.revise import build_revise
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

load_dotenv()

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)

# System prompt for the always-fail sense_check stub. Notes are
# deliberately generic — the stub doesn't see the draft, so it
# can't quote specific content. revise will do *something* with
# these notes; the test isn't about revision quality, it's about
# retry-cap enforcement.
ALWAYS_FAIL_PROMPT = """You are a test stub for sense_check. Your ONLY job is to return
EXACTLY the following text, with no preamble and no closing
commentary:

VERDICT: FAIL

SUMMARY
Test stub: this auditor always returns FAIL to exercise the
orchestrator's revise retry-cap logic. The draft itself may be
fine; ignore that.

FAITHFULNESS ISSUES
- Stubbed failure for retry-cap testing.

STRUCTURE ISSUES
None.

PROSE ISSUES
None.

CONSISTENCY ISSUES
- Stubbed failure for retry-cap testing.

REVISION NOTES
Tighten the news section's opening to lead more directly with
the synthesis's identified dominant narrative. The current
phrasing buries the lead under preamble; the reader should
absorb the main story in the first sentence rather than the
third or fourth.

Output exactly that text. Do not vary it. Do not add commentary
before or after. Do not interpret the input — just produce the
hardcoded response.
"""


def build_always_fail_sense_check() -> Agent:
    """Build a stub sense_check that always returns VERDICT: FAIL."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)
    return Agent(
        name="sense_check",
        description=(
            "Audit the rendered brief against the synthesis. Returns "
            "a verdict (PASS or FAIL) on the first line, then a "
            "structured assessment with faithfulness, structure, "
            "prose, and consistency issues, plus revision notes."
        ),
        system_prompt=ALWAYS_FAIL_PROMPT,
        model=model,
        tools=[],
        callback_handler=None,
    )


def build_orchestrator_with_stub() -> Agent:
    """Build the orchestrator with the always-fail sense_check stub.

    Mirrors build_orchestrator() in orchestrator.py but swaps the
    real sense_check for the stub. All other specialists are real.
    """
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    specialists = [
        build_research_news(),
        build_research_catalysts(),
        build_research_geo(),
        build_synthesise(),
        build_cross_check(),
        build_draft(),
        build_always_fail_sense_check(),  # stub in place of real sense_check
        build_revise(),
    ]

    return Agent(
        name="orchestrator",
        description=("Coordinates a team of specialists to produce a daily " "commodity briefing."),
        system_prompt=load_prompt("orchestrator"),
        model=model,
        tools=[*specialists, fetch_price],
    )


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Failure-path smoke test for sense_check retry loop (region: {region})")
    print(f"Target date: {today}")
    print(
        "Stub: sense_check is wired to always return VERDICT: FAIL. "
        "Watching for retry-cap enforcement.\n"
    )

    orchestrator = build_orchestrator_with_stub()

    invocation_input = f"""Produce today's daily oil briefing.

Target date: {today}
Commodity: crude oil (WTI futures, symbol CL=F)

Briefing specification:
{BRIEFING_SPEC}
"""

    print("Invoking orchestrator with stubbed sense_check...")
    print("=" * 60)

    try:
        result = orchestrator(invocation_input, structured_output_model=FinalBrief)
    except StructuredOutputException as exc:
        print("\nSTRUCTURED OUTPUT VALIDATION FAILED")
        print(f"Error: {exc}")
        print(
            "\nNote: even if sense_check failed twice, the orchestrator should "
            "still proceed to Phase 3 and produce a FinalBrief. If it didn't, "
            "the cap-fallback behaviour ('proceed with the best draft') is "
            "not working."
        )
        return

    print("=" * 60)

    # Best-effort count of sense_check calls from the AgentResult.
    # Falls back to manual count from the streamed Tool #N lines.
    sense_check_calls = 0
    if hasattr(result, "message") and result.message:
        try:
            for content_block in result.message.get("content", []):
                if (
                    isinstance(content_block, dict)
                    and content_block.get("type") == "tool_use"
                    and content_block.get("name") == "sense_check"
                ):
                    sense_check_calls += 1
        except (AttributeError, TypeError):
            pass

    if sense_check_calls == 0:
        sense_check_calls = "unknown (fall back to manual count from streamed output above)"

    print("\n" + "=" * 60)
    print("RETRY-CAP VERIFICATION")
    print("=" * 60)
    print(f"sense_check invocations detected: {sense_check_calls}")
    print(
        "Expected: 2 (one initial call + one retry). More than 2 means the "
        "orchestrator did not honour the retry cap."
    )

    brief = result.structured_output
    if brief is None:
        print("\nNo structured_output on the AgentResult.")
        print("The orchestrator did not produce a FinalBrief — the cap-fallback")
        print("behaviour ('proceed with the best draft after 2 failed cycles')")
        print("is not working.")
        return

    print("\n--- FinalBrief.subject ---")
    print(brief.subject)

    print("\n--- FinalBrief.plain_text_body (first 600 chars) ---")
    print(brief.plain_text_body[:600])
    print(f"\n(plain_text_body total length: {len(brief.plain_text_body)} chars)")

    print("\n" + "=" * 60)
    print("INTERPRETATION GUIDE")
    print("=" * 60)
    print(
        "PASS: sense_check called exactly 2 times, FinalBrief produced, brief is\n"
        "      coherent. The orchestrator stopped at the cap and proceeded.\n"
        "\n"
        "FAIL: sense_check called 3+ times. The retry-cap is not being honoured.\n"
        "      Tighten the orchestrator prompt or add a programmatic safety net.\n"
        "\n"
        "PARTIAL: sense_check called 2 times but no FinalBrief produced. Cap held\n"
        "         but the orchestrator didn't fall back to producing a brief.\n"
    )


if __name__ == "__main__":
    main()
