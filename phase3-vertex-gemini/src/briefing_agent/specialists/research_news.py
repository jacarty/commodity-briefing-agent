"""News research specialist.

ADK LlmAgent that searches for and summarises recent oil-related news.
The first-party `google_search` tool is bound to this specialist — per
STEP-03 design, research domain judgement lives with the specialist,
not the orchestrator.

Returns text. The orchestrator (eventually) calls this specialist as
part of a ParallelAgent and reads its output from session.state via the
`news_research` output_key.

Phase 1 used LangGraph with Tavily. Phase 2 used Strands+Bedrock with
Tavily. Phase 3 uses ADK+Vertex with first-party google_search — the
prompt-port-verbatim hypothesis says the prompt should still produce
ITEM-formatted output regardless. This specialist is the first test of
that hypothesis on Gemini.

Stateless — each invocation is a fresh research task with whatever the
orchestrator passes in as the user message.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

# Description carries the specialist's role/capability for cases where
# an orchestrator might route based on description (sub-agent transfer
# pattern in ADK). Phase 3 uses a custom BaseAgent orchestrator with
# explicit sequencing, so description is informational here — but we
# keep it because it documents the agent for human readers.
DESCRIPTION = (
    "Research recent oil-related news from the last 24 hours. "
    "Returns 3-5 items with headline, source, URL, why it matters, "
    "direction (supports_trend / reverses_trend / neutral), and "
    "timeframe (short_term / structural)."
)


def build_research_news() -> LlmAgent:
    """Build the news research specialist.

    Factory function rather than a module-level constant so that tests
    and tools can build fresh instances without side-effecting at
    import time. Mirrors Phase 2's factory pattern.
    """
    return LlmAgent(
        name="research_news",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("news"),
        tools=[google_search],
        output_key="news_research",
    )
