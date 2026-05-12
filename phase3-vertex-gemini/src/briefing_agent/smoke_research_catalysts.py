"""Manual smoke test for research_catalysts.

Builds the specialist, invokes it via the runner helper, prints the
output for inspection. Same shape as smoke_research_news.

What this proves:
- The catalysts prompt loads from prompts/catalysts.md
- Gemini produces EVENT-formatted output (or 'NO EVENTS' if applicable)
- The prompt-port-verbatim hypothesis (validated for news in PR 1)
  also holds for catalysts

Run with:
    uv run python -m briefing_agent.smoke_research_catalysts

Manual inspection — does the output look like reasonable EVENT
items in the requested format, or 'NO EVENTS' if today has none?
"""

import asyncio
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK; google-genai checks env at import

from briefing_agent.runner import run_specialist  # noqa: E402
from briefing_agent.specialists.research_catalysts import build_research_catalysts  # noqa: E402


async def main() -> None:
    today = date.today().isoformat()
    print("Building research_catalysts specialist (Vertex AI, Gemini 2.5 Flash)\n")

    agent = build_research_catalysts()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Find the scheduled market-moving events for today that are "
        "likely to influence the oil market."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)

    result = await run_specialist(agent, instruction)
    print(result)

    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
