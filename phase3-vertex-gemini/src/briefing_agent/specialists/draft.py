"""Draft specialist.

ADK LlmAgent that renders the synthesis into a 4-section briefing.
Reads the synthesis from session.state; writes the draft brief
to state['draft']. No bound tools — draft reasons over inputs,
doesn't search.

Single factory function. Unlike synthesise (which has initial and
revise variants), draft has only one role: produce the initial
brief. The revision case is handled by the separate `revise`
specialist, which has different responsibilities (targeted edit,
not full re-render).

Stateless across calls.
"""

from google.adk.agents import LlmAgent

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Render the synthesis into a 4-section daily oil briefing. "
    "Sections: PRICE, NEWS, CATALYSTS, GEOPOLITICS. Each section "
    "2-4 paragraphs. Voice: senior analyst briefing colleagues. "
    "Uses the synthesis as source of truth — no facts beyond what "
    "synthesis contains."
)

# Instruction wrapper for draft. Reads the synthesis from state and
# asks the model to produce a brief using the system prompt's format.
INSTRUCTION = (
    "The synthesis team has produced this analysis. Render it into "
    "the four-section briefing format.\n\n"
    "SYNTHESIS:\n{synthesis}\n\n"
    "Produce the brief using the format in your system prompt. "
    "Four sections, in order, no preamble or closing commentary."
)


def build_draft() -> LlmAgent:
    """Build the draft specialist.

    Reads state['synthesis']. Writes to state['draft']. Runs once
    before the rendering audit loop.
    """
    return LlmAgent(
        name="draft",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=load_prompt("draft") + "\n\n---\n\n" + INSTRUCTION,
        output_key="draft",
    )
