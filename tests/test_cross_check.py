from briefing_agent.nodes import cross_check


def _sample_state_with_synthesis():
    """Build a state that includes a plausible synthesis and research."""
    return {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "briefing_spec": {"sections": ["price", "news", "catalysts", "geopolitics"]},
        "research_plan": {
            "price": "Track WTI volatility.",
            "news": "Find oil-related news.",
            "catalysts": "Identify scheduled events.",
            "geopolitics": "Identify themes.",
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
                    "headline": "Oil falls on ceasefire news",
                    "source": "Reuters",
                    "url": "https://example.com",
                    "why_it_matters": "Removes risk premium.",
                    "direction": "reverses_trend",
                    "timeframe": "short_term",
                }
            ]
        },
        "catalyst_research": {"events": []},
        "geo_research": {
            "themes": [
                {
                    "theme": "Hormuz risk",
                    "summary": "Ongoing tensions.",
                    "impact_direction": "bullish",
                    "timeframe": "near_term",
                    "confidence": "high",
                }
            ]
        },
        "synthesis": {
            "dominant_narrative": "Oil down on ceasefire optimism.",
            "price_interpretation": "Sharp drop reflects risk premium reduction.",
            "cross_stream_signals": "News confirms direction; geopolitics flags ongoing risk.",
            "risks_to_view": "Ceasefire could fail.",
            "headline_metrics": ["WTI -4.7%", "Hormuz risk persistent"],
        },
        "cross_check_attempts": 0,
    }


def test_cross_check_returns_required_shape():
    result = cross_check(_sample_state_with_synthesis())
    
    assert "cross_check_result" in result
    assert "cross_check_attempts" in result
    assert "re_research_targets" in result
    
    cc = result["cross_check_result"]
    expected_fields = {
        "passed", "consistency_issues", "calibration_issues",
        "grounding_issues", "re_research_targets", "summary",
    }
    assert set(cc.keys()) == expected_fields


def test_cross_check_increments_attempts():
    result = cross_check(_sample_state_with_synthesis())
    
    assert result["cross_check_attempts"] == 1


def test_cross_check_passed_is_boolean():
    result = cross_check(_sample_state_with_synthesis())
    
    assert isinstance(result["cross_check_result"]["passed"], bool)


def test_cross_check_re_research_targets_are_valid_streams():
    result = cross_check(_sample_state_with_synthesis())
    
    valid_streams = {"price", "news", "catalysts", "geopolitics"}
    for target in result["cross_check_result"]["re_research_targets"]:
        assert target in valid_streams