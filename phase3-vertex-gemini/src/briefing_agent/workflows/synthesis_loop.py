"""Synthesis audit loop.

Wraps cross_check and synthesise_revise in an ADK LoopAgent. The
initial synthesise is NOT inside this loop — it runs once before
the loop, via the orchestrator. This loop is exclusively the
audit-and-revise cycle.

Order matters: cross_check runs FIRST in each iteration.

- Iteration 1: cross_check reads the initial synthesis from state.
  If PASS, calls exit_loop and the loop exits before
  synthesise_revise runs. If FAIL, synthesise_revise runs and
  overwrites state['synthesis'] with a revised version.
- Iteration 2: cross_check reads the revised synthesis. Same
  decision logic.
- After max_iterations=2: the loop exits regardless. If both
  iterations failed audit, state['synthesis'] is the second
  revision and is not freshly audited — the orchestrator will
  proceed with it (cap-fallback per STEP-03 design).

The max_iterations=2 cap matches Phase 2's retry budget exactly.
Phase 1 used 3; Phase 2's retrospective concluded 2 was right.

Per STEP-03, the orchestrator's custom BaseAgent will suppress the
escalate signal coming from this loop's exit so the parent
pipeline doesn't halt.
"""

from google.adk.agents import LoopAgent

from briefing_agent.specialists.cross_check import build_cross_check
from briefing_agent.specialists.synthesise import build_synthesise_revise


def build_synthesis_loop() -> LoopAgent:
    """Build the synthesis audit loop.

    Order: cross_check first, then synthesise_revise. cross_check's
    exit_loop call (on PASS) terminates the loop before
    synthesise_revise runs in that iteration. On FAIL,
    synthesise_revise runs and the loop continues to the next
    iteration.
    """
    return LoopAgent(
        name="synthesis_loop",
        sub_agents=[
            build_cross_check(),
            build_synthesise_revise(),
        ],
        max_iterations=2,
    )
