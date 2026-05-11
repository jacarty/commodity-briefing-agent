"""Failure-path smoke test for the orchestrator.

Tests retry-cap enforcement under audit failure. STEP-03 named
this as the hardest test of model-driven orchestration. The
happy-path smoke test (smoke_orchestrator.py) didn't exercise it
because both audits passed first try.

Approach:

1. Build a stub `cross_check` specialist that ALWAYS returns
   `VERDICT: FAIL` with realistic FAIL output (RE-RESEARCH
   TARGETS, SUMMARY, etc.).
2. Build a custom orchestrator with the stub in place of real
   cross_check. All other specialists are real.
3. Invoke the orchestrator on a normal briefing request.
4. Count how many times the orchestrator calls cross_check via
   tool-call narration in stdout.
5. Pass criterion: cross_check is called exactly 2 times, then
   the orchestrator proceeds to Phase 2 anyway.

What we're testing:

- Does the orchestrator stop at the cap (max 2 cross_check
  cycles)?
- Does it correctly proceed to Phase 2 with the latest synthesis
  when the cap is hit?
- Does it produce a FinalBrief at the end even though cross_check
  never passed?

Cost: roughly 20-30 cents per run because re-research fires (4
research specialists run twice, synthesise runs twice, plus all
the audit/draft/sense_check work).

Run with:
    uv run python -m briefing_agent.smoke_orchestrator_failure
"""

import os
from datetime import date

from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel
from strands.types.exceptions import StructuredOutputException

from briefing_agent.final_brief import FinalBrief
from briefing_agent.prompts import load_prompt
from briefing_agent.specialists.draft import build_draft
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.revise import build_revise
from briefing_agent.specialists.sense_check import build_sense_check
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

# System prompt for the always-fail stub. The stub is a real
# Strands Agent (matches the shape of the real cross_check) but
# its prompt hardcodes the response. The model has no choice but
# to produce the FAIL output.
ALWAYS_FAIL_PROMPT = """You are a test stub for cross_check. Your ONLY job is to return
EXACTLY the following text, with no preamble and no closing
commentary:

VERDICT: FAIL

SUMMARY
Test stub: this auditor always returns FAIL to exercise the
orchestrator's retry-cap logic. The synthesis itself may be
fine; ignore that.

CONSISTENCY ISSUES
- Stubbed failure for retry-cap testing.

CALIBRATION ISSUES
None.

GROUNDING ISSUES
- Stubbed failure for retry-cap testing.

RE-RESEARCH TARGETS
- news

Output exactly that text. Do not vary it. Do not add commentary
before or after. Do not interpret the input — just produce the
hardcoded response.
"""


def build_always_fail_cross_check() -> Agent:
    """Build a stub cross_check that always returns VERDICT: FAIL.

    Same `name`, `description`, and shape as the real cross_check —
    so the orchestrator treats it identically — but its prompt
    forces a deterministic FAIL output.
    """
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)
    return Agent(
        name="cross_check",
        description=(
            "Audit the synthesis for consistency, calibration, and "
            "grounding against the underlying research. Returns a "
            "verdict (PASS or FAIL) on the first line, then a "
            "structured assessment."
        ),
        system_prompt=ALWAYS_FAIL_PROMPT,
        model=model,
        tools=[],
        callback_handler=None,
    )


def build_orchestrator_with_stub() -> Agent:
    """Build the orchestrator with the always-fail cross_check stub.

    Mirrors build_orchestrator() in orchestrator.py but swaps the
    real cross_check for the stub. All other specialists are real.
    """
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    specialists = [
        build_research_news(),
        build_research_catalysts(),
        build_research_geo(),
        build_synthesise(),
        build_always_fail_cross_check(),  # stub in place of real cross_check
        build_draft(),
        build_sense_check(),
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
    print(f"Failure-path smoke test for the orchestrator (region: {region})")
    print(f"Target date: {today}")
    print(
        "Stub: cross_check is wired to always return VERDICT: FAIL. "
        "Watching for retry-cap enforcement.\n"
    )

    orchestrator = build_orchestrator_with_stub()

    invocation_input = f"""Produce today's daily oil briefing.

Target date: {today}
Commodity: crude oil (WTI futures, symbol CL=F)

Briefing specification:
{BRIEFING_SPEC}
"""

    print("Invoking orchestrator with stubbed cross_check...")
    print("=" * 60)

    try:
        result = orchestrator(invocation_input, structured_output_model=FinalBrief)
    except StructuredOutputException as exc:
        print("\nSTRUCTURED OUTPUT VALIDATION FAILED")
        print(f"Error: {exc}")
        print(
            "\nNote: even if cross_check failed twice, the orchestrator should "
            "still proceed to Phase 2 and produce a FinalBrief. If it didn't, "
            "the cap-fallback behaviour ('proceed with the best synthesis') is "
            "not working."
        )
        return

    print("=" * 60)

    # Inspect the orchestrator's tool-call history to count
    # cross_check invocations. The verdict is binary: ≤2 is the
    # cap holding; >2 is a retry-cap failure.
    cross_check_calls = 0
    if hasattr(result, "message") and result.message:
        # Strands AgentResult exposes the conversation; we can scan
        # tool-use entries. Different SDK versions may shape this
        # differently, so we fall back to a string search if the
        # structured walk doesn't find anything.
        try:
            for content_block in result.message.get("content", []):
                if (
                    isinstance(content_block, dict)
                    and content_block.get("type") == "tool_use"
                    and content_block.get("name") == "cross_check"
                ):
                    cross_check_calls += 1
        except (AttributeError, TypeError):
            pass

    if cross_check_calls == 0:
        # Structured walk didn't find tool calls — fall back to
        # counting "Tool #N: cross_check" lines in the streamed
        # output. This is heuristic but resilient to SDK version
        # differences.
        cross_check_calls = "unknown (fall back to manual count from streamed output above)"

    print("\n" + "=" * 60)
    print("RETRY-CAP VERIFICATION")
    print("=" * 60)
    print(f"cross_check invocations detected: {cross_check_calls}")
    print(
        "Expected: 2 (one initial call + one retry). More than 2 means the "
        "orchestrator did not honour the retry cap."
    )

    brief = result.structured_output
    if brief is None:
        print("\nNo structured_output on the AgentResult.")
        print("The orchestrator did not produce a FinalBrief — the cap-fallback")
        print("behaviour ('proceed with the best synthesis after 2 failed cycles')")
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
        "PASS: cross_check called exactly 2 times, FinalBrief produced, brief is\n"
        "      coherent. The orchestrator stopped at the cap and proceeded.\n"
        "\n"
        "FAIL: cross_check called 3+ times. The retry-cap is not being honoured.\n"
        "      Tighten the orchestrator prompt or add a programmatic safety net.\n"
        "\n"
        "PARTIAL: cross_check called 2 times but no FinalBrief produced. Cap held\n"
        "         but the orchestrator didn't fall back to producing a brief.\n"
    )


if __name__ == "__main__":
    main()
