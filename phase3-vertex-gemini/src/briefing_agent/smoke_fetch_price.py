"""Manual smoke test for fetch_price.

Calls the function directly. No ADK, no LLM, no session — fetch_price
is a plain Python function that hits yfinance. Just verify it returns
a sensible-looking PriceSnapshot dict.

Run with:
    uv run python -m briefing_agent.smoke_fetch_price

Manual inspection only — does the dict have the expected keys, are
the numbers in the right ballpark (crude oil $60-$120 range), and is
the last_close_date recent?
"""

import json

from briefing_agent.tools import fetch_price


def main() -> None:
    print("Calling fetch_price() with defaults (CL=F, 365 days)\n")

    snapshot = fetch_price()

    print("-" * 60)
    print(json.dumps(snapshot, indent=2))
    print("-" * 60)
    print()
    print(f"Symbol:           {snapshot['symbol']}")
    print(f"Last close:       ${snapshot['last_close']:.2f} on {snapshot['last_close_date']}")
    print(f"Daily change:     {snapshot['daily_change_pct']:+.2f}%")
    print(f"Intraday range:   {snapshot['range_pct']:.2f}%")
    print(f"5-day avg close:  ${snapshot['five_day_avg_close']:.2f}")
    print(f"20-day avg close: ${snapshot['twenty_day_avg_close']:.2f}")
    print(
        f"52-week range:    ${snapshot['fifty_two_week_low']:.2f} – ${snapshot['fifty_two_week_high']:.2f}"
    )


if __name__ == "__main__":
    main()
