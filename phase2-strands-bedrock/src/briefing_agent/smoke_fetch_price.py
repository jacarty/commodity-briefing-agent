"""Manual smoke test for fetch_price.

Calls the plain @tool function directly, prints the resulting dict,
eyeball the values for sanity. Same low-bar pattern as
smoke_research_news.

The bar this proves:
- yfinance is installed and accessible
- The function returns the PriceSnapshot fields ported from Phase 1
- Numbers look reasonable (positive prices, percentages within
  realistic bounds, dates within the lookback window)

Run with:
    uv run python -m briefing_agent.smoke_fetch_price

Manual inspection only — does the dict have all expected keys, do
the values look like real WTI futures prices?
"""

import json

from briefing_agent.tools import fetch_price


def main() -> None:
    print("Calling fetch_price() with default args (CL=F, 365 days)\n")
    print("-" * 60)
    result = fetch_price()
    print(json.dumps(result, indent=2))
    print("-" * 60)


if __name__ == "__main__":
    main()
