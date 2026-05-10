from briefing_agent.nodes import research_geo


def test_research_geo_returns_geo_research_shape():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"geopolitics": "Identify structural themes affecting oil markets."},
    }
    result = research_geo(state)

    assert "geo_research" in result
    geo = result["geo_research"]
    assert "themes" in geo
    assert isinstance(geo["themes"], list)


def test_research_geo_themes_have_required_fields():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"geopolitics": "Identify structural themes affecting oil markets."},
    }
    result = research_geo(state)

    expected_fields = {
        "theme",
        "summary",
        "impact_direction",
        "timeframe",
        "confidence",
    }

    for theme in result["geo_research"]["themes"]:
        assert set(theme.keys()) == expected_fields
        assert all(isinstance(v, str) for v in theme.values())


def test_research_geo_enums_are_valid():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"geopolitics": "Identify structural themes affecting oil markets."},
    }
    result = research_geo(state)

    valid_directions = {"bullish", "bearish", "ambiguous"}
    valid_timeframes = {"near_term", "medium_term", "long_term"}
    valid_confidence = {"high", "medium", "low"}

    for theme in result["geo_research"]["themes"]:
        assert theme["impact_direction"] in valid_directions
        assert theme["timeframe"] in valid_timeframes
        assert theme["confidence"] in valid_confidence
