"""Orchestrator agent.

Top-level Strands Agent for the daily commodity briefing. Wires
together every specialist as a tool, plus the plain `fetch_price`
tool, and produces a `FinalBrief` as structured output.

This is the only Agent that uses `structured_output_model`. Every
internal specialist returns text; only the boundary is typed.

Streaming: orchestrator runs with default streaming (no
`callback_handler=None`). For dev runs we want to see top-level
reasoning and tool calls. A future deployment may want to silence
this — set `callback_handler=None` at that point.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt
from briefing_agent.specialists.cross_check import build_cross_check
from briefing_agent.specialists.draft import build_draft
from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news
from briefing_agent.specialists.revise import build_revise
from briefing_agent.specialists.sense_check import build_sense_check
from briefing_agent.specialists.synthesise import build_synthesise
from briefing_agent.tools import fetch_price

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"


def build_orchestrator() -> Agent:
    """Build the orchestrator agent.

    Wires every specialist and the fetch_price tool. Returns an
    Agent ready to be invoked with a natural-language input
    describing the target date, commodity, and briefing
    specification.
    """
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    specialists = [
        build_research_news(),
        build_research_catalysts(),
        build_research_geo(),
        build_synthesise(),
        build_cross_check(),
        build_draft(),
        build_sense_check(),
        build_revise(),
    ]

    return Agent(
        name="orchestrator",
        description=(
            "Coordinates a team of specialists to produce a daily "
            "commodity briefing. Plans the workflow, calls research / "
            "synthesise / draft / audit specialists, applies retry "
            "logic on audit failures, and produces a FinalBrief as "
            "structured output."
        ),
        system_prompt=load_prompt("orchestrator"),
        model=model,
        tools=[*specialists, fetch_price],
    )
