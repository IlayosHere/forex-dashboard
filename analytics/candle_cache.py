"""
analytics/candle_cache.py
-------------------------
In-memory caching layer for M15 candle data plus derived series (ATR, H1 bars).

Wraps the existing TradingView data fetcher from strategies/fvg_impulse/data.py
so the analytics engine can access candle history without redundant fetches.
Each CandleCache instance is per-analytics-run (not global/persistent).
"""
from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)

_DEFAULT_BAR_COUNT = 300
_DEFAULT_LOOKBACK = 20


class CandleCache:
    """In-memory cache for M15 candle data, keyed by symbol.

    Also caches ATR series and H1 bars to avoid recomputing them
    once per signal when multiple signals share the same symbol.
    """

    def __init__(self) -> None:
        self._cache: dict[str, pd.DataFrame | None] = {}
        self._atr_cache: dict[str, pd.Series] = {}
        self._h1_cache: dict[str, pd.DataFrame] = {}

    def get(self, symbol: str) -> pd.DataFrame | None:
        """Return cached candles for a symbol, fetching on first access."""
        if symbol not in self._cache:
            self._cache[symbol] = self._fetch(symbol)
        return self._cache[symbol]

    def get_atr(self, symbol: str, period: int = 14) -> pd.Series | None:
        """Return cached ATR series for a symbol, computing on first access."""
        key = f"{symbol}_{period}"
        if key not in self._atr_cache:
            df = self.get(symbol)
            if df is None:
                return None
            self._atr_cache[key] = _compute_atr(df, period)
        return self._atr_cache[key]

    def get_h1(self, symbol: str) -> pd.DataFrame | None:
        """Return cached H1 OHLC bars for a symbol, computing on first access."""
        if symbol not in self._h1_cache:
            df = self.get(symbol)
            if df is None:
                return None
            h1 = df.resample("1h").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last"},
            ).dropna()
            self._h1_cache[symbol] = h1
        return self._h1_cache[symbol]

    def _fetch(self, symbol: str) -> pd.DataFrame | None:
        """Fetch M15 candles from TradingView via existing data layer."""
        from strategies.fvg_impulse.data import get_candles

        logger.info("Fetching candle data for %s", symbol)
        return get_candles(symbol, count=_DEFAULT_BAR_COUNT)

    def warm(self, symbols: list[str]) -> None:
        """Pre-fetch candles for a list of symbols."""
        for symbol in symbols:
            self.get(symbol)

    def clear(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._atr_cache.clear()
        self._h1_cache.clear()

    @property
    def symbols(self) -> list[str]:
        """Return the list of cached symbols."""
        return list(self._cache.keys())


def get_candles_around(
    df: pd.DataFrame,
    target_time: datetime,
    lookback: int = _DEFAULT_LOOKBACK,
) -> pd.DataFrame | None:
    """Slice candles up to target_time with given lookback.

    Returns a slice of ``lookback`` bars ending at or before target_time,
    or None if not enough data.
    """
    target_ts = pd.Timestamp(target_time, tz="UTC")
    subset = df.loc[df.index <= target_ts]

    if len(subset) < lookback:
        logger.warning(
            "Not enough candle data around %s (need %d, have %d)",
            target_time, lookback, len(subset),
        )
        return None

    return subset.iloc[-lookback:]


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute Average True Range over the given period.

    Positions with fewer than ``period`` bars are NaN.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.rolling(window=period, min_periods=period).mean()
