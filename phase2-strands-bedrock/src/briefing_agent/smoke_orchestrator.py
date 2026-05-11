"""End-to-end smoke test for the orchestrator.

Invokes the orchestrator with a single input describing today's
briefing requirements. The orchestrator should plan the workflow,
call every specialist, gate progress on the two auditors, and
produce a FinalBrief as structured output.

This is the first time the orchestrator runs the full workflow.
Several STEP-03 open questions get answered by this test:

- Can the orchestrator manage input-string assembly reliably?
- Does it enforce the two retry loops from prose alone?
- Does it interpret the VERDICT lines correctly?
- Does it produce a valid FinalBrief at the end?

The smoke test does not deliberately corrupt anything — we want
to see the happy-path behaviour. Failure-path testing (forcing
cross_check or sense_check to fail) is something we can add
later if needed.

Cost: roughly 10-15 cents per run (full chain + structured
output).

Run with:
    uv run python -m briefing_agent.smoke_orchestrator

Manual inspection — does the orchestrator:
- Call the four research data sources?
- Call synthesise with their outputs assembled?
- Call cross_check and respond to its verdict?
- Call draft?
- Call sense_check and respond to its verdict?
- Produce a FinalBrief with subject, html_body, plain_text_body?
"""

import os
from datetime import date

from dotenv import load_dotenv
from strands.types.exceptions import StructuredOutputException

from briefing_agent.final_brief import FinalBrief
from briefing_agent.orchestrator import build_orchestrator

load_dotenv()

BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"End-to-end smoke test for the orchestrator (region: {region})")
    print(f"Target date: {today}\n")

    orchestrator = build_orchestrator()

    invocation_input = f"""Produce today's daily oil briefing.

Target date: {today}
Commodity: crude oil (WTI futures, symbol CL=F)

Briefing specification:
{BRIEFING_SPEC}
"""

    print("Invoking orchestrator...")
    print("=" * 60)

    try:
        result = orchestrator(invocation_input, structured_output_model=FinalBrief)
    except StructuredOutputException as exc:
        print("\nSTRUCTURED OUTPUT VALIDATION FAILED")
        print(f"Error: {exc}")
        print(
            "\nThe orchestrator's final response did not match the FinalBrief schema. "
            "Check the prompt's Phase 3 instructions and ensure the orchestrator "
            "produced the three required fields."
        )
        return

    print("=" * 60)

    brief = result.structured_output
    if brief is None:
        print("\nNo structured_output on the AgentResult — unexpected.")
        print(f"Raw result message: {result}")
        return

    print("\n--- FinalBrief.subject ---")
    print(brief.subject)

    print("\n--- FinalBrief.plain_text_body ---")
    print(brief.plain_text_body)

    print("\n--- FinalBrief.html_body (first 500 chars) ---")
    print(brief.html_body[:500])
    print(f"\n(html_body total length: {len(brief.html_body)} chars)")


if __name__ == "__main__":
    main()
