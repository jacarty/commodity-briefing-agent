"""Final brief assembly specialist.

ADK LlmAgent with `output_schema=FinalBrief` that converts the
final draft into the typed FinalBrief deliverable. This is the only
specialist in Phase 3 that uses output_schema; all others use
plain text via output_key.

Reads state['draft'] via template substitution. Produces a
FinalBrief instance — ADK parses the model's JSON output via
Pydantic's model_validate_json and stores the resulting dict in
state['final_brief'].

If the model produces invalid JSON or missing fields, ADK raises
pydantic.ValidationError. The orchestrator catches this and
retries once before giving up — the Generator-Critic pattern for
output_schema reliability discussed in adk-python#3759.

No bound tools — assembly is pure reformatting, no fetch needed.
"""

from google.adk.agents import LlmAgent

from briefing_agent.models import FinalBrief

MODEL_ID = "gemini-2.5-flash"

DESCRIPTION = (
    "Assemble the final 4-section draft into a typed FinalBrief "
    "with subject, html_body, and plain_text_body. The text content "
    "stays unchanged; only the rendering format changes."
)

# Instruction wrapper for final_brief assembly. Reads the draft from
# state. Asks the model to produce a FinalBrief JSON. The
# output_schema enforces the structure; the instruction reinforces
# what the model should produce.
INSTRUCTION = """\
You are the assembly step for the daily oil briefing. The draft
below has already been written and approved by the editor. Your job
is to convert it into a structured FinalBrief.

DRAFT (4-section approved brief):
{draft}

Produce a FinalBrief JSON object with exactly these three fields:

- subject: A concise email subject line. Format:
  "Crude oil briefing — YYYY-MM-DD"
  Use today's date.

- html_body: The full briefing rendered as HTML. Use these tags only:
  - <h2> for section headers (PRICE SECTION, NEWS SECTION, etc.)
  - <p> for paragraphs
  - <strong> for inline emphasis if needed
  Do NOT include <html>, <head>, <body>, or <!DOCTYPE> tags.
  Do NOT include <ul>, <li>, or any list markup — the draft is prose.

- plain_text_body: The full briefing as plain text. Section headers
  on their own lines in UPPERCASE (which they already are in the
  draft). Paragraphs separated by single blank lines.

The text content of the four sections must be preserved exactly.
This is a rendering step, not an editing step.

Respond with ONLY the JSON object. No preamble, no explanation, no
code fences. The structure must validate against the FinalBrief
schema.
"""


def build_final_brief() -> LlmAgent:
    """Build the final_brief assembly specialist.

    Reads state['draft']. Writes a FinalBrief to state['final_brief']
    (as a dict, since ADK stores output_schema'd outputs as the
    parsed JSON structure).
    """
    return LlmAgent(
        name="final_brief",
        model=MODEL_ID,
        description=DESCRIPTION,
        instruction=INSTRUCTION,
        output_schema=FinalBrief,
        output_key="final_brief",
    )
