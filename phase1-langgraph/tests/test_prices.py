from briefing_agent.data_sources.prices import PriceDataSource


def test_fetch_returns_required_fields():
    source = PriceDataSource()
    result = source.fetch("CL=F")

    expected_keys = {
        "symbol",
        "last_close",
        "last_close_date",
        "open",
        "high",
        "low",
        "daily_change_pct",
        "range_pct",
        "five_day_avg_close",
        "twenty_day_avg_close",
        "fifty_two_week_high",
        "fifty_two_week_low",
    }
    assert set(result.keys()) == expected_keys


def test_fetch_returns_floats_and_strings():
    source = PriceDataSource()
    result = source.fetch("CL=F")

    assert isinstance(result["symbol"], str)
    assert isinstance(result["last_close_date"], str)
    assert isinstance(result["last_close"], float)
    assert isinstance(result["high"], float)


def test_fetch_high_at_least_low():
    source = PriceDataSource()
    result = source.fetch("CL=F")

    assert result["high"] >= result["low"]
    assert result["fifty_two_week_high"] >= result["fifty_two_week_low"]


def test_fetch_invalid_symbol_raises():
    import pytest

    source = PriceDataSource()

    with pytest.raises(ValueError):
        source.fetch("DEFINITELY_NOT_A_SYMBOL_XYZ123")
