from briefing_agent.nodes import deliver


def _sample_state_with_brief():
    """State with a synthesis and rendered brief, ready for delivery."""
    return {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "synthesis": {
            "dominant_narrative": (
                "Crude markets caught between Hormuz supply tightness "
                "and emerging demand fragility from China retreat."
            ),
            "price_interpretation": "WTI down 0.28% on volatile session.",
            "cross_stream_signals": "Supply story holds; demand cracks visible.",
            "risks_to_view": "EIA tomorrow could swing thesis materially.",
            "headline_metrics": [
                "WTI -0.28%",
                "OPEC+ +188 kbd",
                "Hormuz 9 mbd offline",
            ],
        },
        "draft": {
            "price_section": (
                "WTI closed at 94.81, down 0.28% on a wide intraday range. "
                "The structural Hormuz premium remains intact even as "
                "today's session showed profit-taking ahead of inventory data."
            ),
            "news_section": (
                "OPEC+ confirmed it cannot materially offset Hormuz losses. "
                "Meanwhile, China is restricting bank lending to refiners "
                "importing Iranian crude — a quiet but material demand shock."
            ),
            "catalysts_section": (
                "API tonight at 4:30 PM ET and EIA tomorrow at 10:30 AM ET "
                "are the day's defining catalysts. Watch for surprises in "
                "either direction."
            ),
            "geopolitics_section": (
                "The market is supply-constrained but increasingly fragile "
                "on the demand side. China's retreat from Iranian oil is "
                "the new variable; existing premiums remain anchored."
            ),
        },
    }


def test_deliver_returns_final_brief_shape():
    result = deliver(_sample_state_with_brief())

    assert "final_brief" in result
    fb = result["final_brief"]

    expected_fields = {"subject", "html_body", "plain_text_body"}
    assert set(fb.keys()) == expected_fields


def test_deliver_subject_is_reasonable_length():
    """Subject should be a single line, not too long for inbox preview."""
    result = deliver(_sample_state_with_brief())

    subject = result["final_brief"]["subject"]
    assert isinstance(subject, str)
    assert "\n" not in subject
    assert 20 <= len(subject) <= 100  # generous bounds


def test_deliver_html_contains_section_structure():
    """HTML should have h2 tags for each section."""
    result = deliver(_sample_state_with_brief())
    html = result["final_brief"]["html_body"]

    # Should have section headers (case-insensitive)
    assert "<h2" in html.lower()
    # All four sections should be represented
    for section in ["price", "news", "catalysts", "geopolitics"]:
        assert section in html.lower()


def test_deliver_plain_text_is_readable():
    """Plain text should be present and structured."""
    result = deliver(_sample_state_with_brief())
    plain = result["final_brief"]["plain_text_body"]

    assert isinstance(plain, str)
    assert len(plain) > 200  # actual content, not a stub
    # Should reference the four sections somehow
    plain_lower = plain.lower()
    for section in ["price", "news", "catalysts", "geopolitics"]:
        assert section in plain_lower
