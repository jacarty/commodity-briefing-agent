"""Sense-check specialist.

Strands Agent that audits the rendered brief against the synthesis
it was meant to render. Second auditor in the agent. Same
`VERDICT: PASS / FAIL` opening-line convention as cross_check —
gives the orchestrator a deterministic routing signal on line 1.

No bound tools, stateless across calls, silent
(`callback_handler=None`). Same tools-less template as cross_check
but checking different things at a different layer (prose-vs-
synthesis rather than synthesis-vs-research).
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Audit the rendered brief against the synthesis. Returns a "
    "verdict (PASS or FAIL) on the first line, then a structured "
    "assessment with faithfulness, structure, prose, and "
    "consistency issues, plus revision notes for the reviser if "
    "failing. Call after draft to gate progress to delivery. Bias "
    "toward passing; only fail when revision would meaningfully "
    "improve the brief. The input should contain the synthesis "
    "and the four-section brief to audit."
)


def build_sense_check() -> Agent:
    """Build the sense_check specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="sense_check",
        description=DESCRIPTION,
        system_prompt=load_prompt("sense_check"),
        model=model,
        tools=[],
        callback_handler=None,
    )
