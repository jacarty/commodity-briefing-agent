"""Cross-check specialist.

ADK LlmAgent that audits the synthesis against the research it
was based on. First auditor in the agent.

Carries the `exit_loop` function tool. The prompt instructs the
model to call exit_loop when its verdict is PASS. On FAIL, the
function is not called, and the parent LoopAgent continues to
the next sub-agent (synthesise_revise).

Returns text starting with `VERDICT: PASS` or `VERDICT: FAIL` per
the Phase 2-ported prompt — the VERDICT line remains the
human-readable signal even though the routing is via function call
in Phase 3.

No search tools — cross_check reasons over inputs, doesn't fetch
new information.
"""

from google.adk.agents import LlmAgent

from briefing_agent.prompts import load_prompt
from briefing_agent.tools import exit_loop

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Audit the synthesis for consistency, calibration, and grounding "
    "against the underlying research. Returns a verdict (PASS or "
    "FAIL) and structured assessment. On PASS, calls exit_loop to "
    "signal the audit loop is complete. Bias toward passing; only "
    "fail on material issues that would mislead a competent reader."
)

# Instruction wrapper for cross_check. Reads the current synthesis
# and the four research streams from state, asks the model to audit
# them. The system prompt (cross_check.md) describes the audit
# methodology and output format including the exit_loop signalling.
INSTRUCTION = (
    "Audit the following synthesis against the research it was built "
    "from. Read carefully before judging.\n\n"
    "SYNTHESIS:\n{synthesis}\n\n"
    "Underlying research:\n\n"
    "PRICE DATA:\n{price_data}\n\n"
    "NEWS RESEARCH:\n{news_research}\n\n"
    "CATALYSTS RESEARCH:\n{catalysts_research}\n\n"
    "GEOPOLITICS RESEARCH:\n{geo_research}\n\n"
    "Produce your assessment using the format in your system prompt. "
    "Begin with VERDICT: PASS or VERDICT: FAIL on the first line. "
    "After producing your full assessment, call exit_loop if your "
    "verdict is PASS. Do not call exit_loop on FAIL."
)


def build_cross_check() -> LlmAgent:
    """Build the cross_check specialist with exit_loop tool bound."""
    return LlmAgent(
        name="cross_check",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("cross_check") + "\n\n---\n\n" + INSTRUCTION,
        tools=[exit_loop],
        output_key="cross_check_result",
    )
