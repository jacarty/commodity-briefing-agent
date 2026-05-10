from briefing_agent.nodes import research_catalysts


def test_research_catalysts_returns_catalyst_research_shape():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"catalysts": "Identify scheduled US energy market events today."},
    }
    result = research_catalysts(state)

    assert "catalyst_research" in result
    cat = result["catalyst_research"]
    assert "events" in cat
    assert isinstance(cat["events"], list)


def test_research_catalysts_events_have_required_fields():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"catalysts": "Identify scheduled US energy market events today."},
    }
    result = research_catalysts(state)

    expected_fields = {
        "name",
        "scheduled_time",
        "consensus",
        "surprise_threshold",
        "importance",
        "notes",
    }

    for event in result["catalyst_research"]["events"]:
        assert set(event.keys()) == expected_fields
        assert all(isinstance(v, str) for v in event.values())


def test_research_catalysts_importance_is_valid():
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {"catalysts": "Identify scheduled US energy market events today."},
    }
    result = research_catalysts(state)

    valid_importance = {"high", "medium", "low"}
    for event in result["catalyst_research"]["events"]:
        assert event["importance"] in valid_importance
