"""Manual smoke test for research_news.

Builds the specialist, invokes it directly with a sample input, prints
the output for inspection. NOT a pytest test — that comes later, once
the orchestrator exists and we have proper end-to-end fixtures.

The bar this proves:
- The specialist agent constructs without errors
- Strands + BedrockModel + tavily_search wire together
- Tavily auth works from .env
- The system prompt loads from the prompts directory
- The specialist returns text the orchestrator (eventually) can read

Run with:
    uv run python -m briefing_agent.smoke_research_news

Manual inspection only — does the output look like 3-5 reasonable
oil news items in the requested format?
"""

import os
from datetime import date

from dotenv import load_dotenv

from briefing_agent.specialists.research_news import build_research_news

load_dotenv()


def main() -> None:
    today = date.today().isoformat()
    print(f"Building research_news specialist (region: {os.getenv('AWS_REGION')})\n")

    agent = build_research_news()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Find the most important oil-related news from the last 24 hours "
        "for today's briefing."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)
    result = agent(instruction)
    print(result)
    print("-" * 60)


if __name__ == "__main__":
    main()
