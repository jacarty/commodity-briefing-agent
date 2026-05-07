from briefing_agent.nodes import draft


def _sample_state_with_synthesis():
    return {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "briefing_spec": {
            "sections": ["price", "news", "catalysts", "geopolitics"],
            "audience": "trading desk",
            "tone": "professional analyst",
        },
        "synthesis": {
            "dominant_narrative": (
                "Oil is collapsing on geopolitical de-escalation — "
                "US-Iran ceasefire signals are overriding structural "
                "tightness in the inventory data."
            ),
            "price_interpretation": (
                "Today's 4.5% drop reflects a violent risk-premium repricing, "
                "not demand weakness. Buyers are stepping in below $90."
            ),
            "cross_stream_signals": (
                "News and price stream agree on direction; geopolitics flags "
                "the Hormuz reopening as the dominant catalyst, but signals "
                "structural OPEC+ disruption that will persist."
            ),
            "risks_to_view": (
                "Ceasefire could collapse on a single incident; refinery outages "
                "remain real; OPEC+ may discipline more than expected."
            ),
            "headline_metrics": [
                "WTI -4.5% on ceasefire news",
                "Hormuz transit at 2 mbd vs 20 mbd pre-war",
                "Iraq offering crude at $33/bbl discount",
            ],
        },
    }


def test_draft_returns_brief_shape():
    result = draft(_sample_state_with_synthesis())
    
    assert "draft" in result
    brief = result["draft"]
    
    expected_fields = {
        "price_section", "news_section",
        "catalysts_section", "geopolitics_section",
    }
    assert set(brief.keys()) == expected_fields


def test_draft_sections_are_non_empty_strings():
    result = draft(_sample_state_with_synthesis())
    brief = result["draft"]
    
    for section in ["price_section", "news_section",
                    "catalysts_section", "geopolitics_section"]:
        assert isinstance(brief[section], str)
        assert len(brief[section]) > 100  # actual prose, not a one-liner


def test_draft_includes_metrics_somewhere():
    """Headline metrics from synthesis should appear in the brief somewhere."""
    result = draft(_sample_state_with_synthesis())
    brief = result["draft"]
    
    full_brief = " ".join([
        brief["price_section"],
        brief["news_section"],
        brief["catalysts_section"],
        brief["geopolitics_section"],
    ])
    
    # At minimum, the most distinctive number should appear somewhere.
    # 4.5% is the most specific, distinctive metric in the sample.
    assert "4.5" in full_brief or "4.5%" in full_brief