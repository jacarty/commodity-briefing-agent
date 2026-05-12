"""Geopolitics research specialist.

ADK LlmAgent that identifies and assesses structural and macro themes
shaping the oil market — supply security, OPEC+ dynamics, major-
producer politics, demand-side macro, energy transition, trade and
currency.

`google_search` is bound directly to this specialist. Returns text via
the `geo_research` output_key. Stateless across calls.

Same shape as research_news; see that file for the rationale on
factory function, description text, and tool binding.

Note: the prompt file is `geopolitics.md` (matching Phase 1/2's
filename), but the specialist name is `research_geo` for brevity in
tool listings.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Research structural and macro geopolitical themes shaping the "
    "oil market — supply security, OPEC+ dynamics, major-producer "
    "politics, demand-side macro, energy transition, trade and "
    "currency. Returns 3-5 distinct themes with summary, impact "
    "direction (bullish / bearish / ambiguous), timeframe "
    "(near_term / medium_term / long_term), and confidence "
    "(high / medium / low)."
)


def build_research_geo() -> LlmAgent:
    """Build the geopolitics research specialist."""
    return LlmAgent(
        name="research_geo",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("geopolitics"),
        tools=[google_search],
        output_key="geo_research",
    )
