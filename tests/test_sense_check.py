from briefing_agent.nodes import sense_check


def _sample_state_with_brief():
    """Build a state with a plausible synthesis and brief."""
    return {
        "target_date": "2026-05-07",
        "commodity": "crude_oil",
        "synthesis": {
            "dominant_narrative": (
                "Oil markets are caught between supply tightness from "
                "Hormuz disruption and demand weakness from China slowdown."
            ),
            "price_interpretation": (
                "WTI's modest gain to $96 masks volatile intraday range; "
                "buyers defending support but no breakout conviction."
            ),
            "cross_stream_signals": (
                "News and geopolitics agree on supply tightness; price "
                "action suggests demand-side concerns are dominant."
            ),
            "risks_to_view": (
                "Hormuz reopening could collapse premium; China stimulus "
                "could revive demand; OPEC+ discipline could fracture further."
            ),
            "headline_metrics": [
                "WTI closed at $96",
                "Hormuz closure 9 mbd offline",
                "OPEC+ June increase of 188,000 bpd",
            ],
        },
        "draft": {
            "price_section": (
                "WTI closed at $96 today after a volatile session. The "
                "modest gain masks deep uncertainty: the intraday range "
                "was 7% and buyers defended support around $89.85. "
                "Five-day average sits above today's close, suggesting "
                "momentum has rolled over despite a structurally bullish "
                "supply story."
            ),
            "news_section": (
                "OPEC+ announced a 188,000 bpd increase for June, but "
                "the move is largely symbolic given Hormuz remains closed. "
                "Nine million barrels per day of Gulf production is "
                "offline, making any quota adjustment inoperative until "
                "shipping resumes."
            ),
            "catalysts_section": (
                "The EIA inventory report at 10:30 AM ET is today's key "
                "data point. A surprise draw would reinforce supply "
                "tightness; a build would validate demand-weakness fears. "
                "Watch refinery utilization and import figures for "
                "demand-side signals."
            ),
            "geopolitics_section": (
                "China demand softness is the structural headwind that "
                "market is pricing despite the bullish supply backdrop. "
                "OPEC+ cohesion is fracturing — UAE's exit removed spare "
                "capacity, and members are signaling production "
                "increases. The market is voting that demand destruction "
                "outweighs supply disruption."
            ),
        },
        "sense_check_attempts": 0,
    }


def test_sense_check_returns_required_shape():
    result = sense_check(_sample_state_with_brief())

    assert "sense_check_result" in result
    assert "sense_check_attempts" in result

    sc = result["sense_check_result"]
    expected_fields = {
        "passed",
        "faithfulness_issues",
        "structure_issues",
        "prose_issues",
        "consistency_issues",
        "revision_notes",
        "summary",
    }
    assert set(sc.keys()) == expected_fields


def test_sense_check_increments_attempts():
    result = sense_check(_sample_state_with_brief())

    assert result["sense_check_attempts"] == 1


def test_sense_check_passed_is_boolean():
    result = sense_check(_sample_state_with_brief())

    assert isinstance(result["sense_check_result"]["passed"], bool)


def test_sense_check_revision_notes_is_string():
    result = sense_check(_sample_state_with_brief())

    assert isinstance(result["sense_check_result"]["revision_notes"], str)
