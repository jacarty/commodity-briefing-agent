"""Manual smoke test for research_catalysts.

Same low-bar pattern as smoke_research_news. Builds the specialist,
invokes it directly, prints the output for inspection.

Run with:
    uv run python -m briefing_agent.smoke_research_catalysts

Manual inspection only — does the output list today's catalysts
in the requested EVENT N format, or report NO EVENTS if the day
genuinely has none?
"""

import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.research_catalysts import build_research_catalysts

load_dotenv()


def main() -> None:
    today = date.today().isoformat()
    print(f"Building research_catalysts specialist (region: {os.getenv('AWS_REGION')})\n")

    agent = build_research_catalysts()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Find the scheduled market-moving events for today that are "
        "likely to affect the oil market."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)
    result = agent(instruction)
    print(result)
    print("-" * 60)


if __name__ == "__main__":
    main()
