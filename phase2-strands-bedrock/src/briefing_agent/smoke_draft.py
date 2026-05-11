"""Live-chain smoke test for draft.

Runs the full upstream chain — fetch_price, research_news,
research_catalysts, research_geo, synthesise — then feeds the
synthesis (plus briefing spec and target date) to draft.

This exercises the rendering pattern end-to-end. There's no
orchestrator yet, so this script performs the input assembly that
the orchestrator's prompt will eventually encode.

Cost: roughly the same as smoke_synthesise plus one extra
specialist call. ~3-5 cents per run.

Run with:
    uv run python -m briefing_agent.smoke_draft

Manual inspection only — does the brief have all four section
headers in the right order? Is each section 2-4 paragraphs? Are
the synthesis's HEADLINE METRICS embedded in prose somewhere? No
bullet points, no internal headers?
"""

import json
import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.draft import build_draft
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


def main() -> None:
    today = date.today().isoformat()
    region = os.getenv("AWS_REGION")
    print(f"Live-chain smoke test for draft (region: {region})")
    print(f"Target date: {today}\n")

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

    print("[5/6] synthesise...")
    synthesise_agent = build_synthesise()
    synthesise_input = assemble_synthesise_input(
        target_date=today,
        price_data=price_data,
        news_text=news_text,
        catalysts_text=catalysts_text,
        geo_text=geo_text,
    )
    synthesis_text = str(synthesise_agent(synthesise_input))

    print("[6/6] draft...")
    draft_agent = build_draft()
    draft_input = assemble_draft_input(today, synthesis_text)
    result = draft_agent(draft_input)

    print("\n" + "=" * 60)
    print("DRAFT OUTPUT")
    print("=" * 60)
    print(result)
    print("=" * 60)


if __name__ == "__main__":
    main()
