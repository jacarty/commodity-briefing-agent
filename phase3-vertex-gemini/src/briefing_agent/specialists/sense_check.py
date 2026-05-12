"""Sense-check specialist.

ADK LlmAgent that audits the rendered brief against the synthesis
it was built from. Second auditor in the agent (cross_check is
the first, in the synthesis loop).

Carries the `exit_loop` function tool — same pattern as cross_check.
The prompt instructs the model to call exit_loop when its verdict
is PASS. On FAIL, exit_loop is not called and the parent LoopAgent
continues to the revise specialist.

Returns text starting with `VERDICT: PASS` or `VERDICT: FAIL` per
the Phase 2-ported prompt. Note: on PASS the response is the
exit_loop function call only — no text part (this is documented
behaviour from PR 3; see STEP-06 for the empty-state-on-PASS
finding). PR 5 orchestrator detects PASS via function_call events,
not state parsing.

No search tools — sense_check reasons over inputs, doesn't fetch
new information.
"""

from google.adk.agents import LlmAgent

from briefing_agent.prompts import load_prompt
from briefing_agent.tools import exit_loop

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Audit the rendered brief for faithfulness to synthesis, "
    "structural soundness, prose quality, and internal consistency. "
    "Returns a verdict (PASS or FAIL) and structured assessment. On "
    "PASS, calls exit_loop to signal the rendering loop is complete. "
    "Bias toward passing; only fail when revision would meaningfully "
    "improve the brief for the reader."
)

# Instruction wrapper for sense_check. Reads the current draft and
# the synthesis it was built from, asks the model to audit. The
# system prompt (sense_check.md) describes the audit methodology
# and output format including exit_loop signalling.
INSTRUCTION = (
    "Audit the following brief against the synthesis it was built "
    "from. Read carefully before judging.\n\n"
    "SYNTHESIS (source of truth):\n{synthesis}\n\n"
    "DRAFT BRIEF:\n{draft}\n\n"
    "Produce your assessment using the format in your system prompt. "
    "Begin with VERDICT: PASS or VERDICT: FAIL on the first line. "
    "After producing your full assessment, call exit_loop if your "
    "verdict is PASS. Do not call exit_loop on FAIL."
)


def build_sense_check() -> LlmAgent:
    """Build the sense_check specialist with exit_loop tool bound."""
    return LlmAgent(
        name="sense_check",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("sense_check") + "\n\n---\n\n" + INSTRUCTION,
        tools=[exit_loop],
        output_key="sense_check_result",
    )
