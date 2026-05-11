"""Cross-check specialist.

Strands Agent that audits the synthesis against the research it
was based on. First auditor in the agent. Returns text starting
with `VERDICT: PASS` or `VERDICT: FAIL` per the STEP-03 design
— the VERDICT line is the structural mitigation that gives the
orchestrator a near-deterministic routing signal without breaking
the text-native pattern.

No bound tools — cross_check reasons over inputs, doesn't search.
Stateless across calls. Silent (`callback_handler=None`).
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Audit the synthesis for consistency, calibration, and grounding "
    "against the underlying research. Returns a verdict (PASS or "
    "FAIL) on the first line, then a structured assessment with "
    "consistency, calibration, grounding issues, and re-research "
    "targets. Call after synthesise to gate progress to the drafter. "
    "Bias toward passing; only fail on material issues that would "
    "mislead a competent reader. The input should contain the "
    "synthesis and all four research outputs."
)


def build_cross_check() -> Agent:
    """Build the cross_check specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="cross_check",
        description=DESCRIPTION,
        system_prompt=load_prompt("cross_check"),
        model=model,
        tools=[],
        callback_handler=None,
    )
