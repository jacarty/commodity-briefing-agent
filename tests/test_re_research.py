from briefing_agent.nodes import re_research, _format_feedback


def test_re_research_with_no_targets_returns_empty():
    state = {
        "re_research_targets": [],
        "cross_check_result": {
            "consistency_issues": [],
            "calibration_issues": [],
            "grounding_issues": [],
        },
    }
    result = re_research(state)
    assert result == {}


def test_re_research_clears_targets_after_running():
    """When targets exist, after re-research runs, they should be cleared."""
    # We're testing the structural behaviour, not actual research output.
    # This will hit the API since news is a real research function.
    # If you want to skip the API hit, mark this @pytest.mark.integration
    # and configure pytest to skip integration by default.
    state = {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "research_plan": {
            "news": "Find oil-related news.",
        },
        "re_research_targets": ["news"],
        "cross_check_result": {
            "consistency_issues": ["News stream missed source X"],
            "calibration_issues": [],
            "grounding_issues": [],
        },
    }
    result = re_research(state)

    assert "re_research_targets" in result
    assert result["re_research_targets"] == []
    assert "news_research" in result  # the re-research wrote new news_research


def test_format_feedback_includes_relevant_issues():
    """Feedback should include issues mentioning the stream by name."""
    cross_check_result = {
        "consistency_issues": [
            "News stream missed important source X",
            "Geopolitics overlooked Iran",
        ],
        "calibration_issues": [
            "News confidence too high relative to source quality",
        ],
        "grounding_issues": [],
    }

    feedback = _format_feedback("news", cross_check_result)

    assert "News stream missed important source X" in feedback
    assert "News confidence too high" in feedback
    assert "Geopolitics overlooked Iran" not in feedback


def test_format_feedback_with_no_relevant_issues_uses_generic_message():
    """When no issues mention the stream, still produce a useful instruction."""
    cross_check_result = {
        "consistency_issues": [],
        "calibration_issues": [],
        "grounding_issues": [],
    }

    feedback = _format_feedback("news", cross_check_result)

    assert "re-research" in feedback.lower()
