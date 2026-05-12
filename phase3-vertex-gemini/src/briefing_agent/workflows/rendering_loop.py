"""Rendering audit loop.

Wraps sense_check and revise in an ADK LoopAgent. The initial
draft is NOT inside this loop — it runs once before the loop, via
the orchestrator. This loop is exclusively the audit-and-revise
cycle for the brief.

Mirrors the synthesis_loop pattern (PR 3): critic first, refiner
second.

- Iteration 1: sense_check reads the initial draft from state.
  If PASS, calls exit_loop and the loop exits before revise runs.
  If FAIL, revise runs and overwrites state['draft'] with a
  revised version.
- Iteration 2: sense_check reads the revised draft. Same decision
  logic.
- After max_iterations=2: the loop exits regardless. If both
  iterations failed audit, state['draft'] is the second revision
  and is not freshly audited — orchestrator proceeds with it
  (cap-fallback per STEP-03 design).

max_iterations=2 matches synthesis_loop. Phase 1 used 3 iterations
on the rendering loop; Phase 2 retrospective concluded 2 was
right for both loops.

Per STEP-03, the orchestrator's custom BaseAgent will suppress the
escalate signal from this loop's exit so the parent pipeline
doesn't halt (LoopAgent-escalate-propagation issue from #1376).
"""

from google.adk.agents import LoopAgent

from briefing_agent.specialists.revise import build_revise
from briefing_agent.specialists.sense_check import build_sense_check


def build_rendering_loop() -> LoopAgent:
    """Build the rendering audit loop.

    Order: sense_check first, then revise. sense_check's exit_loop
    call (on PASS) terminates the loop before revise runs in that
    iteration. On FAIL, revise runs and the loop continues to the
    next iteration.
    """
    return LoopAgent(
        name="rendering_loop",
        sub_agents=[
            build_sense_check(),
            build_revise(),
        ],
        max_iterations=2,
    )
