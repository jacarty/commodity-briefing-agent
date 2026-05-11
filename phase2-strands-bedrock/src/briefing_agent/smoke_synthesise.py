"""Live-chain smoke test for synthesise.

Runs the full upstream chain — fetch_price, research_news,
research_catalysts, research_geo — then concatenates their outputs
into a single input string and feeds it to the synthesise specialist.

This is the first end-to-end exercise of the input-assembly pattern
STEP-03 flagged. There's no orchestrator yet, so this script
performs the assembly that the orchestrator's prompt will eventually
encode. The point is to see whether synthesise produces coherent
output when given realistic upstream content.

Cost: four specialist calls plus one synthesise call, plus their
Tavily searches. Single-digit cents per run. Keep runs to one or
two for smoke purposes.

Run with:
    uv run python -m briefing_agent.smoke_synthesise

Manual inspection only — does the synthesis have all five section
headers in the right order? Does CROSS-STREAM SIGNALS actually
reference inter-stream patterns? Are the HEADLINE METRICS specific
and grounded in the research?
"""

import json
import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

load_dotenv()

# Editorial intent for the brief. Phase 1 had this as `briefing_spec`
# in state; in Phase 2 the orchestrator will pass it as part of the
# synthesise input string. Kept simple for smoke testing.
BRIEFING_SPEC = (
    "Daily oil briefing for a desk of senior analysts. Four prose "
    "sections (price, news, catalysts, geopolitics). Voice: senior "
    "analyst briefing colleagues — direct, evidence-led, professional "
    "but not stuffy. Length: 2-4 paragraphs per section."
)


def assemble_synthesise_input(
    target_date: str,
    price_data: dict,
    news_text: str,
    catalysts_text: str,
    geo_text: str,
) -> str:
    """Concatenate the four research outputs into a single string.

    This is the input-assembly logic the orchestrator's prompt will
    eventually encode. For now, the smoke test does it directly.
    """
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


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Live-chain smoke test for synthesise (region: {region})")
    print(f"Target date: {today}\n")

    # Step 1: gather research from all four sources.
    print("[1/5] fetch_price...")
    price_data = fetch_price()
    print(f"      Last close: ${price_data['last_close']:.2f} on {price_data['last_close_date']}")

    print("[2/5] research_news...")
    news_agent = build_research_news()
    news_text = str(
        news_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the most important oil-related news from the last 24 hours."
        )
    )

    print("[3/5] research_catalysts...")
    catalysts_agent = build_research_catalysts()
    catalysts_text = str(
        catalysts_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Find the scheduled market-moving events for today."
        )
    )

    print("[4/5] research_geo...")
    geo_agent = build_research_geo()
    geo_text = str(
        geo_agent(
            f"Target date: {today}. Commodity: crude oil. "
            f"Identify the structural and macro themes shaping the market."
        )
    )

    # Step 2: assemble the input string and call synthesise.
    print("[5/5] synthesise...")
    synthesise_input = assemble_synthesise_input(
        target_date=today,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )

    synthesise_agent = build_synthesise()
    result = synthesise_agent(synthesise_input)

    print("\n" + "=" * 60)
    print("SYNTHESIS OUTPUT")
    print("=" * 60)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    main()
