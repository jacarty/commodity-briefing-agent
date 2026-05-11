"""Manual smoke test for research_geo.

Same low-bar pattern as smoke_research_news. Builds the specialist,
invokes it directly, prints the output for inspection.

Run with:
    uv run python -m briefing_agent.smoke_research_geo

Manual inspection only — does the output list 3-5 distinct
geopolitical themes in the requested THEME N format with sensible
direction/timeframe/confidence calls?
"""

import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.research_geo import build_research_geo

load_dotenv()


def main() -> None:
    today = date.today().isoformat()
    print(f"Building research_geo specialist (region: {os.getenv('AWS_REGION')})\n")

    agent = build_research_geo()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Identify the structural and macro themes currently shaping "
        "the oil market."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)
    result = agent(instruction)
    print(result)
    print("-" * 60)


if __name__ == "__main__":
    main()
