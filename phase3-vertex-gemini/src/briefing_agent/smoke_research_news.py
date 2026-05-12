"""Manual smoke test for research_news.

Builds the specialist, invokes it via the runner helper, prints the
output for inspection. NOT a pytest test — that comes later, once the
orchestrator exists and we have proper end-to-end fixtures.

What this proves:
- The specialist agent constructs without errors
- ADK + Vertex + Gemini 2.5 Flash + google_search wire together
- The prompt loads from prompts/news.md
- The specialist returns text the orchestrator (eventually) can read
- The prompt-port-verbatim hypothesis holds: Gemini produces
  ITEM-formatted output the same way Haiku did in Phase 2

Run with:
    uv run python -m briefing_agent.smoke_research_news

Manual inspection — does the output look like 3-5 reasonable oil news
items in the ITEM N format with all required fields?
"""

import asyncio
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK; google-genai checks env at import

from briefing_agent.runner import run_specialist  # noqa: E402
from briefing_agent.specialists.research_news import build_research_news  # noqa: E402


async def main() -> None:
    today = date.today().isoformat()
    print("Building research_news specialist (Vertex AI, Gemini 2.5 Flash)\n")

    agent = build_research_news()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Find the most important oil-related news from the last 24 hours "
        "for today's briefing."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)

    result = await run_specialist(agent, instruction)
    print(result)

    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
