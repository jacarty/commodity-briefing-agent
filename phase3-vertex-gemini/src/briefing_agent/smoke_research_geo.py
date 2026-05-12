"""Manual smoke test for research_geo.

Builds the specialist, invokes it via the runner helper, prints the
output for inspection. Same shape as smoke_research_news.

What this proves:
- The geopolitics prompt loads from prompts/geopolitics.md
- Gemini produces THEME-formatted output
- The prompt-port-verbatim hypothesis holds for geopolitics

Run with:
    uv run python -m briefing_agent.smoke_research_geo

Manual inspection — does the output look like 3-5 distinct THEME
items in the requested format, with sensible classification fields?
"""

import asyncio
from datetime import date

from dotenv import load_dotenv

load_dotenv()  # before importing ADK; google-genai checks env at import

from briefing_agent.runner import run_specialist  # noqa: E402
from briefing_agent.specialists.research_geo import build_research_geo  # noqa: E402


async def main() -> None:
    today = date.today().isoformat()
    print("Building research_geo specialist (Vertex AI, Gemini 2.5 Flash)\n")

    agent = build_research_geo()

    instruction = (
        f"Target date: {today}. Commodity: crude oil. "
        "Identify the structural and macro geopolitical themes "
        "currently shaping the oil market."
    )

    print(f"Invoking with: {instruction!r}\n")
    print("-" * 60)

    result = await run_specialist(agent, instruction)
    print(result)

    print("-" * 60)


if __name__ == "__main__":
    asyncio.run(main())
