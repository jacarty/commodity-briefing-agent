"""Live-chain smoke test for cross_check.

Two scenarios:

1. **PASS scenario** — run the full upstream chain (research → synthesise),
   feed the real synthesis to cross_check, expect `VERDICT: PASS` because
   the synthesis is genuinely grounded in the research.

2. **FAIL scenario** — run the same upstream chain, then corrupt the
   synthesis by inserting a fabricated claim (a specific number that
   doesn't appear in any research). Feed the corrupted synthesis to
   cross_check, expect `VERDICT: FAIL` flagging the fabricated fact as
   a grounding issue.

Tests both behaviours:
- Pass-bias works (cross_check doesn't over-flag legitimate synthesis)
- Detection works (cross_check catches a real fabrication)

Cost: roughly 2x what smoke_synthesise costs (we run the upstream chain
once, then call cross_check twice). Single-digit cents per run total.

Run with:
    uv run python -m briefing_agent.smoke_cross_check

Manual inspection only — does VERDICT: PASS appear on the first line of
the first run? Does VERDICT: FAIL appear on the first line of the second
run, with a GROUNDING ISSUES entry mentioning the fabricated number?
"""

import json
import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.cross_check import build_cross_check
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

load_dotenv()

BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)

# The fabricated claim to inject for the FAIL scenario. Specific
# enough that cross_check should flag it as ungrounded, plausible
# enough that the fabrication is meaningful (i.e., not "the price
# is $999/barrel").
FABRICATED_CLAIM = (
    "Goldman Sachs raised its 2027 oil price forecast to $147 per "
    "barrel in a research note published this morning."
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


def assemble_cross_check_input(
    target_date: str,
    synthesis_text: str,
    price_data: dict,
    news_text: str,
    catalysts_text: str,
    geo_text: str,
) -> str:
    return f"""Target date: {target_date}
Commodity: crude oil

=== SYNTHESIS TO REVIEW ===
{synthesis_text}

=== UNDERLYING RESEARCH ===

--- PRICE DATA ---
{json.dumps(price_data, indent=2)}

--- NEWS RESEARCH ---
{news_text}

--- CATALYSTS RESEARCH ---
{catalysts_text}

--- GEOPOLITICS RESEARCH ---
{geo_text}
"""


def corrupt_synthesis(synthesis_text: str) -> str:
    """Inject a fabricated claim into the HEADLINE METRICS section.

    Returns a copy of the synthesis with one extra bullet that
    isn't grounded in any research. The rest of the synthesis is
    unchanged.
    """
    marker = "HEADLINE METRICS"
    idx = synthesis_text.find(marker)
    if idx == -1:
        # Defensive: if the marker isn't present, append the
        # fabrication at the end. cross_check should still flag
        # it, even if it's positioned oddly.
        return synthesis_text + f"\n\nFABRICATED ADDITION:\n- {FABRICATED_CLAIM}\n"
    # Find the end of the HEADLINE METRICS section (next blank line
    # after the header) and inject the fabricated bullet just before.
    section_start = idx + len(marker)
    return (
        synthesis_text[:section_start] + f"\n- {FABRICATED_CLAIM}" + synthesis_text[section_start:]
    )


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Live-chain smoke test for cross_check (region: {region})")
    print(f"Target date: {today}\n")

    # Gather research from all four sources.
    print("[1/6] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}")

    print("[2/6] research_news...")
    news_agent = build_research_news()
    news_text = str(
        news_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the most important oil-related news from the last 24 hours."
        )
    )

    print("[3/6] research_catalysts...")
    catalysts_agent = build_research_catalysts()
    catalysts_text = str(
        catalysts_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the scheduled market-moving events for today."
        )
    )

    print("[4/6] research_geo...")
    geo_agent = build_research_geo()
    geo_text = str(
        geo_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Identify the structural and macro themes shaping the market."
        )
    )

    # Run synthesise once; we'll use the output for both cross_check runs.
    print("[5/6] synthesise...")
    synthesise_agent = build_synthesise()
    synthesise_input = assemble_synthesise_input(
        target_date=today,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )
    real_synthesis = str(synthesise_agent(synthesise_input))

    # Build the cross_check specialist once; reuse for both scenarios.
    print("[6/6] cross_check (both scenarios)...")
    cross_check_agent = build_cross_check()

    # SCENARIO 1: PASS case (real synthesis, expect VERDICT: PASS).
    print("\n" + "=" * 60)
    print("SCENARIO 1: PASS case (real synthesis)")
    print("=" * 60)
    pass_input = assemble_cross_check_input(
        target_date=today,
        synthesis_text=real_synthesis,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )
    pass_result = cross_check_agent(pass_input)
    print(pass_result)

    # SCENARIO 2: FAIL case (corrupted synthesis, expect VERDICT: FAIL).
    print("\n" + "=" * 60)
    print("SCENARIO 2: FAIL case (synthesis corrupted with fabricated claim)")
    print(f"Injected claim: {FABRICATED_CLAIM!r}")
    print("=" * 60)
    corrupted_synthesis = corrupt_synthesis(real_synthesis)
    fail_input = assemble_cross_check_input(
        target_date=today,
        synthesis_text=corrupted_synthesis,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )
    fail_result = cross_check_agent(fail_input)
    print(fail_result)


if __name__ == "__main__":
    main()
