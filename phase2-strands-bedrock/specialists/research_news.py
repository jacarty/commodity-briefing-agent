"""News research specialist.

Strands Agent that searches for and summarises recent oil-related news.
Tavily is bound directly to this specialist (per the design decision
in STEP-03 — research domain judgement lives with the specialist, not
the orchestrator).

Returns text. The orchestrator calls this specialist with a string
input describing the run (target date, commodity, any specific
instructions or feedback) and reads the text response.

Stateless across calls — Strands' default for agents passed as tools.
Each invocation is a fresh research task with whatever the orchestrator
passes in.

Silent (`callback_handler=None`) so specialist output doesn't stream
to stdout when the orchestrator calls it.
"""

import os

from strands import Agent
from strands.models import BedrockModel

from briefing_agent.prompts import load_prompt
from briefing_agent.tools import tavily_search

MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

# Description the orchestrator reads to decide when to call this
# specialist. Keep it specific — describes the expertise, not the
# mechanics.
DESCRIPTION = (
    "Research recent oil-related news from the last 24 hours. "
    "Returns 3-5 items with headline, source, URL, why it matters, "
    "direction (supports_trend / reverses_trend / neutral), and "
    "timeframe (short_term / structural). Call when the briefing "
    "needs a news roundup, or to re-research with feedback when an "
    "auditor flags news-related issues."
)


def build_research_news() -> Agent:
    """Build the news research specialist.

    Factory function rather than a module-level constant so that
    tests and tools can build fresh instances with different config
    (e.g. a different model for cheaper test runs) without
    side-effecting at import time.
    """
    region = os.getenv("AWS_REGION")
    model = BedrockModel(model_id=MODEL_ID, region_name=region)

    return Agent(
        name="research_news",
        description=DESCRIPTION,
        system_prompt=load_prompt("news"),
        model=model,
        tools=[tavily_search],
        callback_handler=None,
    )
