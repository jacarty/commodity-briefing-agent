"""Parallel research stage.

Wraps the three research specialists (news, catalysts, geo) in an
ADK ParallelAgent so they execute concurrently. STEP-03 named this
explicitly: the three streams are independent (no specialist needs
another's output), so parallel execution is a free latency win.

ParallelAgent mechanics:
- Each sub-agent runs in its own InvocationContext branch
- All sub-agents share the same session.state
- Each sub-agent writes to its own output_key — no race conditions
  because the keys are distinct
- Events from sub-agents may interleave in the runner's event stream
- The ParallelAgent has no single "final response" — the results
  live in session.state after the run completes

The custom orchestrator (PR 5) will call this ParallelAgent as the
first stage of the pipeline, then read the three state keys
(`news_research`, `catalysts_research`, `geo_research`) to feed
downstream agents.
"""

from google.adk.agents import ParallelAgent

from briefing_agent.specialists.research_catalysts import build_research_catalysts
from briefing_agent.specialists.research_geo import build_research_geo
from briefing_agent.specialists.research_news import build_research_news


def build_research_parallel() -> ParallelAgent:
    """Build the parallel research stage.

    Factory function rather than a module-level constant so a fresh
    instance can be built per pipeline run. Each sub-specialist is
    also built fresh, matching the factory pattern used elsewhere.
    """
    return ParallelAgent(
        name="research_parallel",
        sub_agents=[
            build_research_news(),
            build_research_catalysts(),
            build_research_geo(),
        ],
    )
