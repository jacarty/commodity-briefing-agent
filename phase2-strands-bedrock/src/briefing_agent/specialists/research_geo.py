"""Geopolitics research specialist.

Strands Agent that identifies and assesses structural and macro
themes shaping the oil market — supply security, OPEC+ dynamics,
major-producer politics, demand-side macro, energy transition,
trade and currency.

Tavily bound directly to this specialist. Returns text. Stateless
across calls. Silent (`callback_handler=None`).

Same shape as research_news; see that file for the rationale on
factory function, callback handler, and tool binding.

Note: the prompt file is `geopolitics.md` (matching Phase 1's
filename), but the specialist name is `research_geo` for
brevity in tool listings.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt
from briefing_agent.tools import tavily_search

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Research structural and macro geopolitical themes shaping the "
    "oil market — supply security, OPEC+ dynamics, major-producer "
    "politics, demand-side macro, energy transition, trade and "
    "currency. Returns 3-5 distinct themes with summary, impact "
    "direction (bullish / bearish / ambiguous), timeframe "
    "(near_term / medium_term / long_term), and confidence "
    "(high / medium / low). Call when the briefing needs the "
    "structural backdrop, or to re-research with feedback when an "
    "auditor flags geopolitical issues."
)


def build_research_geo() -> Agent:
    """Build the geopolitics research specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="research_geo",
        description=DESCRIPTION,
        system_prompt=load_prompt("geopolitics"),
        model=model,
        tools=[tavily_search],
        callback_handler=None,
    )
