from briefing_agent.nodes import research_news


def test_research_news_returns_news_research_shape():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"news": "Find any oil-related news from the last 24 hours."},
    }
    result = research_news(state)

    assert "news_research" in result
    news = result["news_research"]
    assert "items" in news
    assert isinstance(news["items"], list)


def test_research_news_items_have_required_fields():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"news": "Find any oil-related news from the last 24 hours."},
    }
    result = research_news(state)

    expected_fields = {
        "headline",
        "source",
        "url",
        "why_it_matters",
        "direction",
        "timeframe",
    }

    for item in result["news_research"]["items"]:
        assert set(item.keys()) == expected_fields
        assert all(isinstance(v, str) for v in item.values())


def test_research_news_direction_is_valid():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"news": "Find any oil-related news from the last 24 hours."},
    }
    result = research_news(state)

    valid_directions = {"supports_trend", "reverses_trend", "neutral"}
    for item in result["news_research"]["items"]:
        assert item["direction"] in valid_directions
