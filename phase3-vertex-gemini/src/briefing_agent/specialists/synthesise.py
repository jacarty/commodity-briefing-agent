"""Synthesise specialist.

ADK LlmAgent that reads the four research streams plus price data
and produces a structured cross-stream view of the day's market.

Phase 3 has two factory functions because the synthesise role is
exercised in two places:

1. **Initial synthesise** (`build_synthesise`) — runs once before
   the audit loop. Reads research from state, writes synthesis.

2. **Revise synthesise** (`build_synthesise_revise`) — runs inside
   the audit loop on iteration 2+. Reads the previous synthesis
   AND the auditor's feedback, writes a revised synthesis that
   addresses the issues.

Both share the same system prompt (synthesise.md). The difference
is in the instruction wrapper: the revise variant is told to
read `{cross_check_result}` and address the issues raised.

Same output_key for both — `synthesis` — using ADK's state-
overwriting pattern (the doc example for refinement loops). The
cross_check agent always reads `{synthesis}` and gets the latest
version.

No tools — synthesise reasons over inputs, doesn't search.
"""

from google.adk.agents import LlmAgent

from briefing_agent.prompts import load_prompt

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION_INITIAL = (
    "Synthesise the four research streams (price, news, catalysts, "
    "geopolitics) into a coherent cross-stream view of the day's "
    "oil market. Produces five sections: DOMINANT NARRATIVE, PRICE "
    "INTERPRETATION, CROSS-STREAM SIGNALS, RISKS TO VIEW, HEADLINE "
    "METRICS. Runs once after research completes."
)

DESCRIPTION_REVISE = (
    "Revise the synthesis based on cross_check feedback. Reads the "
    "previous synthesis, the audit's findings, and the underlying "
    "research, then produces a revised synthesis that addresses "
    "the issues raised. Runs inside the synthesis audit loop after "
    "a FAIL verdict."
)

# Instruction wrapper for the initial synthesise. Reads four research
# streams from state and asks the model to produce a synthesis using
# the system prompt's format.
INITIAL_INSTRUCTION = (
    "Today's research streams have produced the following outputs.\n\n"
    "PRICE DATA:\n{price_data}\n\n"
    "NEWS RESEARCH:\n{news_research}\n\n"
    "CATALYSTS RESEARCH:\n{catalysts_research}\n\n"
    "GEOPOLITICS RESEARCH:\n{geo_research}\n\n"
    "Produce a structured synthesis using the format in your system "
    "prompt. Five sections, in order, no preamble or closing commentary."
)

# Instruction wrapper for the revise variant. Reads the previous
# synthesis and the audit's feedback, asks the model to produce a
# revised synthesis addressing the issues.
REVISE_INSTRUCTION = (
    "An earlier synthesis was audited and FAILED. You're being asked "
    "to revise it.\n\n"
    "PREVIOUS SYNTHESIS:\n{synthesis}\n\n"
    "AUDIT FEEDBACK:\n{cross_check_result}\n\n"
    "Underlying research (unchanged):\n\n"
    "PRICE DATA:\n{price_data}\n\n"
    "NEWS RESEARCH:\n{news_research}\n\n"
    "CATALYSTS RESEARCH:\n{catalysts_research}\n\n"
    "GEOPOLITICS RESEARCH:\n{geo_research}\n\n"
    "Produce a revised synthesis that addresses each issue raised in "
    "the audit feedback. Use the same five-section format as the "
    "system prompt describes. Do not include audit-response commentary; "
    "produce the revised synthesis directly."
)


def build_synthesise() -> LlmAgent:
    """Build the initial synthesise specialist.

    Reads the four research streams from session.state. Writes the
    synthesis to state['synthesis']. Runs once before the audit loop.
    """
    return LlmAgent(
        name="synthesise",
        model=MODEL_ID,
        description=DESCRIPTION_INITIAL,
        instruction=load_prompt("synthesise") + "\n\n---\n\n" + INITIAL_INSTRUCTION,
        output_key="synthesis",
    )


def build_synthesise_revise() -> LlmAgent:
    """Build the revise variant of the synthesise specialist.

    Reads the previous synthesis AND the auditor's feedback. Writes
    a revised synthesis back to state['synthesis'] (overwrites).
    Runs inside the audit loop after a FAIL verdict.
    """
    return LlmAgent(
        name="synthesise_revise",
        model=MODEL_ID,
        description=DESCRIPTION_REVISE,
        instruction=load_prompt("synthesise") + "\n\n---\n\n" + REVISE_INSTRUCTION,
        output_key="synthesis",
    )
