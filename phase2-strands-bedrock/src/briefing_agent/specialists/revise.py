"""Revise specialist.

Strands Agent that produces a revised brief addressing the specific
issues sense_check flagged. Targeted revision, not a rewrite — only
flagged sections change, everything else passes through.

Same output structure as draft (four section headers). No bound
tools, stateless across calls, silent (`callback_handler=None`).

In Phase 1 this was often idle code — sense_check usually passed
first time. Same is likely true here; the component exists for the
cases where it does fire.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

DESCRIPTION = (
    "Revise the brief to address specific issues flagged by "
    "sense_check. Targeted revision — only flagged sections "
    "change; unflagged sections pass through verbatim. Returns "
    "the same four-section structure as draft. Call only when "
    "sense_check returns VERDICT: FAIL with actionable revision "
    "notes. The input should contain the synthesis (source of "
    "truth), the current draft, and the revision notes."
)


def build_revise() -> Agent:
    """Build the revise specialist."""
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="revise",
        description=DESCRIPTION,
        system_prompt=load_prompt("revise"),
        model=model,
        tools=[],
        callback_handler=None,
    )
