"""Catalysts research specialist.

Strands Agent that searches for and structures today's scheduled
market-moving events for the oil market — EIA reports, OPEC+
meetings, major earnings, macro data releases.

Tavily bound directly to this specialist. Returns text. Stateless
across calls. Silent (`callback_handler=None`).

Same shape as research_news; see that file for the rationale on
factory function, callback handler, and tool binding.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt
from briefing_agent.tools import tavily_search

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Research today's scheduled market-moving events for the oil "
    "market — EIA reports, OPEC+ meetings, major company earnings, "
    "macro data releases. Returns a list of events with scheduled "
    "time, consensus, surprise threshold, importance "
    "(high / medium / low), and notes. Returns 'NO EVENTS' on days "
    "with no major catalysts. Call when the briefing needs the "
    "scheduled-events landscape for the target date, or to "
    "re-research with feedback when an auditor flags catalyst-"
    "related issues."
)


def build_research_catalysts() -> Agent:
    """Build the catalysts research specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="research_catalysts",
        description=DESCRIPTION,
        system_prompt=load_prompt("catalysts"),
        model=model,
        tools=[tavily_search],
        callback_handler=None,
    )
