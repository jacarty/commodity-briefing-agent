"""Phase 3 tools.

`fetch_price` is a plain Python function — no ADK tool decorator. Per
STEP-03 design, the custom orchestrator calls it directly:

    price = fetch_price()
    ctx.session.state["price_data"] = price

No LLM wrapper. Deterministic data, no reason for an agent layer.

If a future change requires fetch_price to be available to a specialist
(e.g. price-aware re-research), wrap it with `google.adk.tools.FunctionTool`
at that point. For now: plain function.

Phase 1's PriceSnapshot shape is preserved verbatim — same fields, same
units, same definitions. Phase 2 was the same; Phase 3 keeps it.
"""

from dataclasses import asdict, dataclass

import yfinance as yf

__all__ = ["fetch_price", "PriceSnapshot"]


@dataclass
class PriceSnapshot:
    """Daily price snapshot for a futures contract.

    Field meanings (match Phase 1 and Phase 2 exactly):
        symbol: yfinance ticker (e.g. "CL=F" for WTI crude futures)
        last_close: most recent closing price
        last_close_date: ISO date of last_close
        open/high/low: most recent session OHLC
        daily_change_pct: percent change vs previous close
        range_pct: (high - low) / open, as a percent
        five_day_avg_close: trailing 5-session mean close
        twenty_day_avg_close: trailing 20-session mean close
        fifty_two_week_high/low: extremes over the lookback window
    """

    symbol: str
    last_close: float
    last_close_date: str
    open: float
    high: float
    low: float
    daily_change_pct: float
    range_pct: float
    five_day_avg_close: float
    twenty_day_avg_close: float
    fifty_two_week_high: float
    fifty_two_week_low: float


def fetch_price(symbol: str = "CL=F", days: int = 365) -> dict:
    """Fetch a daily price snapshot for a futures contract.

    Returns the most recent session's OHLC plus derived metrics
    (daily change, intraday range, moving averages, 52-week extremes).
    Uses yfinance; no LLM involved.

    Args:
        symbol: yfinance ticker. Defaults to "CL=F" (WTI crude futures).
        days: Lookback window for moving averages and 52-week range.
            Defaults to 365 (one trading year).

    Returns:
        Dict with the PriceSnapshot fields. Keys are stable across calls
        and match Phase 1 / Phase 2's PriceSnapshot exactly.

    Raises:
        ValueError: If the symbol returns no price history.
    """
    ticker = yf.Ticker(symbol)
    history = ticker.history(period=f"{days}d")

    if history.empty:
        raise ValueError(f"No price history returned for {symbol!r}")

    last_row = history.iloc[-1]
    prev_close = history["Close"].iloc[-2]

    snapshot = PriceSnapshot(
        symbol=symbol,
        last_close=float(last_row["Close"]),
        last_close_date=history.index[-1].strftime("%Y-%m-%d"),
        open=float(last_row["Open"]),
        high=float(last_row["High"]),
        low=float(last_row["Low"]),
        daily_change_pct=float((last_row["Close"] - prev_close) / prev_close * 100),
        range_pct=float((last_row["High"] - last_row["Low"]) / last_row["Open"] * 100),
        five_day_avg_close=float(history["Close"].tail(5).mean()),
        twenty_day_avg_close=float(history["Close"].tail(20).mean()),
        fifty_two_week_high=float(history["High"].max()),
        fifty_two_week_low=float(history["Low"].min()),
    )
    return asdict(snapshot)
