"""Synthesise specialist.

Strands Agent that reads the four research streams plus price data
and produces a structured cross-stream view of the day's market.

First non-research specialist. Differs from the research specialists
in two ways:

1. **No bound tools.** Synthesise reasons over inputs the orchestrator
   provides; it doesn't search for new information.
2. **Different output shape.** Five mandatory section headers
   (DOMINANT NARRATIVE, PRICE INTERPRETATION, CROSS-STREAM SIGNALS,
   RISKS TO VIEW, HEADLINE METRICS) rather than a repeating
   ITEM/EVENT/THEME structure.

Stateless across calls. Silent (`callback_handler=None`).
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Synthesise the four research streams (price, news, catalysts, "
    "geopolitics) into a coherent cross-stream view of the day's "
    "oil market. Produces five sections: DOMINANT NARRATIVE, PRICE "
    "INTERPRETATION, CROSS-STREAM SIGNALS, RISKS TO VIEW, HEADLINE "
    "METRICS. Call after all research is gathered. The input should "
    "contain all four research outputs together with the target "
    "date and the briefing's editorial intent."
)


def build_synthesise() -> Agent:
    """Build the synthesise specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="synthesise",
        description=DESCRIPTION,
        system_prompt=load_prompt("synthesise"),
        model=model,
        tools=[],
        callback_handler=None,
    )
