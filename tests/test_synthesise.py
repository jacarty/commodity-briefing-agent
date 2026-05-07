from briefing_agent.nodes import synthesise


def _sample_state():
    """Build a minimal state with realistic-shaped research outputs."""
    return {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "briefing_spec": {"sections": ["price", "news", "catalysts", "geopolitics"]},
        "research_plan": {
            "price": "Track WTI volatility and key levels.",
            "news": "Find oil-related news from the last 24 hours.",
            "catalysts": "Identify scheduled US energy events.",
            "geopolitics": "Identify structural themes affecting oil markets.",
        },
        "price_research": {
            "symbol": "CL=F",
            "last_close": 91.5,
            "last_close_date": "2026-05-07",
            "open": 96.0,
            "high": 96.5,
            "low": 90.0,
            "daily_change_pct": -4.7,
            "range_pct": 6.8,
            "five_day_avg_close": 99.5,
            "twenty_day_avg_close": 96.4,
            "fifty_two_week_high": 119.5,
            "fifty_two_week_low": 55.0,
        },
        "news_research": {
            "items": [
                {
                    "headline": "Sample headline",
                    "source": "Sample source",
                    "url": "https://example.com",
                    "why_it_matters": "Sample why.",
                    "direction": "supports_trend",
                    "timeframe": "short_term",
                }
            ]
        },
        "catalyst_research": {"events": []},
        "geo_research": {
            "themes": [
                {
                    "theme": "Sample theme",
                    "summary": "Sample summary.",
                    "impact_direction": "ambiguous",
                    "timeframe": "near_term",
                    "confidence": "medium",
                }
            ]
        },
    }


def test_synthesise_returns_synthesis_shape():
    result = synthesise(_sample_state())

    assert "synthesis" in result
    syn = result["synthesis"]

    expected_fields = {
        "dominant_narrative",
        "price_interpretation",
        "cross_stream_signals",
        "risks_to_view",
        "headline_metrics",
    }
    assert set(syn.keys()) == expected_fields


def test_synthesise_string_fields_are_strings():
    result = synthesise(_sample_state())
    syn = result["synthesis"]

    for field in [
        "dominant_narrative",
        "price_interpretation",
        "cross_stream_signals",
        "risks_to_view",
    ]:
        assert isinstance(syn[field], str)
        assert len(syn[field]) > 0  # not empty


def test_synthesise_headline_metrics_is_list_of_strings():
    result = synthesise(_sample_state())
    syn = result["synthesis"]

    assert isinstance(syn["headline_metrics"], list)
    assert all(isinstance(m, str) for m in syn["headline_metrics"])
    assert len(syn["headline_metrics"]) >= 1
