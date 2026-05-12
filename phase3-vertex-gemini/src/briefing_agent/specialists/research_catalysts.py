"""Catalysts research specialist.

ADK LlmAgent that searches for and structures today's scheduled
market-moving events for the oil market — EIA reports, OPEC+
meetings, major earnings, macro data releases.

`google_search` is bound directly to this specialist. Returns text via
the `catalysts_research` output_key. Stateless across calls.

Same shape as research_news; see that file for the rationale on
factory function, description text, and tool binding.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Research today's scheduled market-moving events for the oil "
    "market — EIA reports, OPEC+ meetings, major company earnings, "
    "macro data releases. Returns a list of events with scheduled "
    "time, consensus, surprise threshold, importance "
    "(high / medium / low), and notes. Returns 'NO EVENTS' on days "
    "with no major catalysts."
)


def build_research_catalysts() -> LlmAgent:
    """Build the catalysts research specialist."""
    return LlmAgent(
        name="research_catalysts",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("catalysts"),
        tools=[google_search],
        output_key="catalysts_research",
    )
