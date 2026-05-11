"""Draft specialist.

Strands Agent that renders the synthesis into the four-section
briefing format. Reads the synthesis as source of truth; produces
prose with four mandatory section headers (PRICE SECTION, NEWS
SECTION, CATALYSTS SECTION, GEOPOLITICS SECTION).

No bound tools — draft reasons over the synthesis the orchestrator
provides; it doesn't search for new information. Stateless across
calls. Silent (`callback_handler=None`).

Same tools-less template as synthesise and cross_check.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Render the synthesis into the daily oil briefing — four prose "
    "sections (PRICE, NEWS, CATALYSTS, GEOPOLITICS), 2-4 paragraphs "
    "each. Uses the synthesis as source of truth: don't introduce "
    "facts not in the synthesis; embed headline metrics in prose; "
    "lead with the most important content in each section. Call "
    "after cross_check passes. The input should contain the "
    "synthesis and the briefing's editorial intent."
)


def build_draft() -> Agent:
    """Build the draft specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="draft",
        description=DESCRIPTION,
        system_prompt=load_prompt("draft"),
        model=model,
        tools=[],
        callback_handler=None,
    )
