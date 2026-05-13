"""Phase 3 FinalBrief schema.

Pydantic BaseModel that ports verbatim from Phase 2. Three fields:
- subject — email subject line for the briefing
- html_body — HTML-rendered version of the brief
- plain_text_body — plain-text version for clients that don't render HTML

ADK uses Pydantic's model_validate_json internally for output_schema
enforcement. On Gemini 2.0+ via Vertex AI, this is supported
natively via the _OutputSchemaRequestProcessor.

If the model produces invalid output (missing fields, wrong types),
ADK raises pydantic.ValidationError. There's no automatic retry —
PR 5's orchestrator catches the error and re-runs the assembly step
once before giving up (the discussion at adk-python#3759 suggested
this Generator-Critic pattern for output_schema reliability).
"""

from pydantic import BaseModel, Field


class FinalBrief(BaseModel):
    """The final briefing deliverable.

    Ports verbatim from Phase 1 and Phase 2 — three fields, same
    semantics. The orchestrator's last step produces this shape;
    downstream consumers (email, Slack, etc.) read it.
    """

    subject: str = Field(
        description=(
            "Concise email subject line for the briefing. "
            "Example: 'Crude oil briefing — 2026-05-12'"
        )
    )
    html_body: str = Field(
        description=(
            "HTML-rendered version of the briefing. Should be a "
            "valid HTML fragment (no <html> or <body> tags), "
            "suitable for embedding in an email body. Section "
            "headers as <h2>, paragraphs as <p>."
        )
    )
    plain_text_body: str = Field(
        description=(
            "Plain-text version of the briefing for clients that "
            "don't render HTML. Section headers as UPPERCASE on "
            "their own line, paragraphs separated by blank lines."
        )
    )
