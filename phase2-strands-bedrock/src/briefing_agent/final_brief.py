"""FinalBrief — structured output for the orchestrator.

The orchestrator's `structured_output_model`. This is the only
structured-data boundary in the agent (per STEP-03's design): every
internal specialist returns text, but the orchestrator's final output
is typed because a downstream email service consumes it.

Same shape as Phase 1's FinalBrief — subject, html_body,
plain_text_body. Phase 1 had this as the output of the deliver node;
Phase 2 collapses deliver into the orchestrator's own output.
"""

from pydantic import BaseModel, Field


class FinalBrief(BaseModel):
    """Email-ready output of the daily briefing agent.

    Fields:
        subject: Email subject line. Concise, dated, includes commodity.
        html_body: HTML rendering of the brief for email clients.
        plain_text_body: Plain-text rendering for clients that don't
            support HTML or for previewing.
    """

    subject: str = Field(
        ...,
        description=(
            "Email subject line. Concise, dated, includes commodity. "
            "Example: 'Crude oil briefing — 2026-05-12'."
        ),
    )
    html_body: str = Field(
        ...,
        description=(
            "HTML rendering of the four-section brief. Each section "
            "wrapped in <section> or <div> tags, headings as <h2>, "
            "paragraphs as <p>. No external CSS; inline styles only "
            "if needed."
        ),
    )
    plain_text_body: str = Field(
        ...,
        description=(
            "Plain-text rendering of the four-section brief. Section "
            "headers in uppercase, paragraphs separated by blank "
            "lines. Readable as-is in any text client."
        ),
    )
