"""Revise specialist.

ADK LlmAgent that produces a revised brief addressing the specific
issues sense_check flagged. **Targeted revision, not a rewrite** —
the prompt's central behavioural test is whether the model
preserves unflagged sections and only revises the flagged ones.

Reads state['synthesis'] (source of truth), state['draft']
(current brief), and state['sense_check_result'] (audit feedback).
Writes back to state['draft'] (overwrites), following ADK's
state-overwriting pattern from the docs (initial draft + revise
share the key; sense_check always reads the latest via {draft}).

No bound tools — revise reasons over inputs, doesn't search.

In Phase 1 this was often idle — sense_check usually passed first
time. Same is likely true here; the component exists for the
cases where it does fire.
"""

from google.adk.agents import LlmAgent

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Revise the brief to address specific issues flagged by "
    "sense_check. Targeted revision — only flagged sections "
    "change; unflagged sections pass through verbatim. Returns "
    "the same four-section structure as draft. Runs inside the "
    "rendering audit loop after a FAIL verdict."
)

# Instruction wrapper for revise. Reads the synthesis, the current
# draft, and the sense_check feedback, asks the model to produce a
# revised draft. The system prompt (revise.md) emphasises targeted
# revision rather than full rewrite.
INSTRUCTION = (
    "An earlier brief was audited and FAILED. You're being asked to "
    "revise it. This is a targeted revision — only change what was "
    "flagged.\n\n"
    "SYNTHESIS (source of truth):\n{synthesis}\n\n"
    "CURRENT DRAFT:\n{draft}\n\n"
    "AUDIT FEEDBACK:\n{sense_check_result}\n\n"
    "Produce the revised brief using the four-section format. "
    "Address each issue raised in the audit feedback; preserve "
    "unflagged sections verbatim. No preamble, no closing "
    "commentary, no change-summary."
)


def build_revise() -> LlmAgent:
    """Build the revise specialist.

    Reads the synthesis, current draft, and audit feedback. Writes
    revised draft back to state['draft'] (overwrites). Runs inside
    the rendering audit loop after a FAIL verdict.
    """
    return LlmAgent(
        name="revise",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("revise") + "\n\n---\n\n" + INSTRUCTION,
        output_key="draft",
    )
