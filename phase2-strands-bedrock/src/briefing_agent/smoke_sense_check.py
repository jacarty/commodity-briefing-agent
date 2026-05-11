"""Live-chain smoke test for sense_check.

Two scenarios, same dual-scenario pattern as smoke_cross_check:

1. **PASS scenario** — run the full chain (research → synthesise →
   draft), feed the real brief to sense_check, expect VERDICT: PASS
   because the brief faithfully renders its synthesis.

2. **FAIL scenario** — run the same chain, then corrupt the draft
   by injecting a faithfulness violation (modify a section so it
   contradicts the synthesis). Feed the corrupted brief to
   sense_check, expect VERDICT: FAIL flagging the contradiction
   as a faithfulness issue.

Tests both behaviours:
- Pass-bias works (sense_check doesn't over-flag legitimate brief)
- Detection works (sense_check catches a real faithfulness drift)

Cost: roughly 3-6 cents per run (one full chain plus two
sense_check calls).

Run with:
    uv run python -m briefing_agent.smoke_sense_check

Manual inspection only — does VERDICT: PASS appear on the first
line of the first run? Does VERDICT: FAIL appear on the first
line of the second run, with a FAITHFULNESS ISSUES entry pointing
at the injected contradiction?
"""

import json
import os
import re
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.draft import build_draft
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.sense_check import build_sense_check
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

load_dotenv()

BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)

# Faithfulness corruption: prepend a sentence to the NEWS SECTION
# that flatly contradicts whatever the synthesis identified as the
# dominant news. The injected sentence is intentionally specific
# and bullish-leaning so it's clearly out of step with the rest of
# the brief, which we expect to be largely bearish-or-mixed in the
# current market.
FAITHFULNESS_CORRUPTION = (
    "Today's news flow points to a clear bearish setup: peace "
    "negotiations have produced a binding ceasefire framework, and "
    "the Strait of Hormuz is set to reopen to full traffic within "
    "48 hours."
)


def assemble_synthesise_input(
    target_date: str,
    price_data: dict,
    news_text: str,
    catalysts_text: str,
    geo_text: str,
) -> str:
    return f"""Target date: {target_date}
Commodity: crude oil

Briefing specification:
{BRIEFING_SPEC}

Research outputs follow. Read across all four streams before
writing.

=== PRICE DATA ===
{json.dumps(price_data, indent=2)}

=== NEWS RESEARCH ===
{news_text}

=== CATALYSTS RESEARCH ===
{catalysts_text}

=== GEOPOLITICS RESEARCH ===
{geo_text}
"""


def assemble_draft_input(target_date: str, synthesis_text: str) -> str:
    return f"""Target date: {target_date}
Commodity: crude oil

Briefing specification:
{BRIEFING_SPEC}

=== SYNTHESIS TO RENDER ===
{synthesis_text}
"""


def assemble_sense_check_input(target_date: str, synthesis_text: str, draft_text: str) -> str:
    return f"""Target date: {target_date}
Commodity: crude oil

=== SYNTHESIS (SOURCE OF TRUTH) ===
{synthesis_text}

=== BRIEF TO REVIEW ===
{draft_text}
"""


def corrupt_draft(draft_text: str) -> str:
    """Inject a faithfulness-violating sentence at the start of NEWS SECTION.

    The injected sentence is bullish-bearish-flipped from what
    synthesis would normally support in the current market. The
    rest of the draft is unchanged.

    Looks for `NEWS SECTION` header (case-insensitive) and inserts
    the corruption as the new first sentence of that section.
    """
    pattern = re.compile(r"(NEWS SECTION\s*\n)", re.IGNORECASE)
    match = pattern.search(draft_text)
    if not match:
        # Defensive: if no NEWS SECTION marker, append at the end.
        return draft_text + f"\n\nCORRUPTED ADDITION: {FAITHFULNESS_CORRUPTION}\n"
    insert_at = match.end()
    return draft_text[:insert_at] + FAITHFULNESS_CORRUPTION + " " + draft_text[insert_at:]


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Live-chain smoke test for sense_check (region: {region})")
    print(f"Target date: {today}\n")

    print("[1/7] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}")

    print("[2/7] research_news...")
    news_agent = build_research_news()
    news_text = str(
        news_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the most important oil-related news from the last 24 hours."
        )
    )

    print("[3/7] research_catalysts...")
    catalysts_agent = build_research_catalysts()
    catalysts_text = str(
        catalysts_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the scheduled market-moving events for today."
        )
    )

    print("[4/7] research_geo...")
    geo_agent = build_research_geo()
    geo_text = str(
        geo_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Identify the structural and macro themes shaping the market."
        )
    )

    print("[5/7] synthesise...")
    synthesise_agent = build_synthesise()
    synthesise_input = assemble_synthesise_input(
        target_date=today,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )
    synthesis_text = str(synthesise_agent(synthesise_input))

    print("[6/7] draft...")
    draft_agent = build_draft()
    draft_input = assemble_draft_input(today, synthesis_text)
    real_draft = str(draft_agent(draft_input))

    print("[7/7] sense_check (both scenarios)...")
    sense_check_agent = build_sense_check()

    print("\n" + "=" * 60)
    print("SCENARIO 1: PASS case (real draft)")
    print("=" * 60)
    pass_input = assemble_sense_check_input(today, synthesis_text, real_draft)
    pass_result = sense_check_agent(pass_input)
    print(pass_result)

    print("\n" + "=" * 60)
    print("SCENARIO 2: FAIL case (draft corrupted with faithfulness violation)")
    print(f"Injected sentence: {FAITHFULNESS_CORRUPTION!r}")
    print("=" * 60)
    corrupted_draft = corrupt_draft(real_draft)
    fail_input = assemble_sense_check_input(today, synthesis_text, corrupted_draft)
    fail_result = sense_check_agent(fail_input)
    print(fail_result)


if __name__ == "__main__":
    main()
