from dataclasses import dataclass, asdict
import yfinance as yf


@dataclass
class PriceSnapshot:
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


class PriceDataSource:
    """Wraps a price data API behind a stable interface."""

    def fetch(self, symbol: str, days: int = 365) -> dict:
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
