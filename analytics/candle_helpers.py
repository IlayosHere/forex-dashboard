"""
analytics/candle_helpers.py
---------------------------
DataFrame-level helpers for derived candle series (ATR, H1, D1, EMA).

These are separate from the cache layer so param modules can import only
what they need without pulling in the full CandleCache infrastructure.

All ``cached_*`` functions memoize their result in a module-level
``WeakValueDictionary`` keyed by ``id(df)``. ``CandleCache`` hands the same
DataFrame object to every signal in a single enrichment run, so the key is
stable for the duration of a request. When the cache expires the old
DataFrame becomes unreferenced and the WeakValueDictionary entries drop out
naturally — no manual eviction needed.
"""
from __future__ import annotations

import logging
import weakref
from datetime import datetime

import pandas as pd

from shared.market_data import EXCHANGE_TZ

logger = logging.getLogger(__name__)

_DEFAULT_LOOKBACK = 20

# ---------------------------------------------------------------------------
# DataFrame-scoped memoization stores
# ---------------------------------------------------------------------------

_atr_memo: weakref.WeakValueDictionary[tuple[int, int], pd.Series] = (
    weakref.WeakValueDictionary()
)
_h1_memo: weakref.WeakValueDictionary[int, pd.DataFrame] = (
    weakref.WeakValueDictionary()
)
_d1_memo: weakref.WeakValueDictionary[int, pd.DataFrame] = (
    weakref.WeakValueDictionary()
)
_ema20_h1_memo: weakref.WeakValueDictionary[int, pd.Series] = (
    weakref.WeakValueDictionary()
)


def clear_memos() -> None:
    """Clear all module-level memoization stores.

    Called by ``CandleCache.clear()`` so that derived series (ATR, H1, D1,
    EMA-20) are evicted together with the underlying candle entries, ensuring
    no stale derived data survives a cache reset.
    """
    _atr_memo.clear()
    _h1_memo.clear()
    _d1_memo.clear()
    _ema20_h1_memo.clear()


# ---------------------------------------------------------------------------
# Slice helper
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# ATR computation
# ---------------------------------------------------------------------------

def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
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


# ---------------------------------------------------------------------------
# Cached derived series
# ---------------------------------------------------------------------------

def cached_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Return the ATR series for ``df``, computing on first access and
    memoizing across callers that share the same DataFrame instance."""
    key = (id(df), period)
    series = _atr_memo.get(key)
    if series is None:
        series = _compute_atr(df, period)
        _atr_memo[key] = series
    return series


def cached_h1(df: pd.DataFrame) -> pd.DataFrame:
    """Return the H1 resample of ``df``, memoized per-DataFrame instance."""
    key = id(df)
    cached = _h1_memo.get(key)
    if cached is not None:
        return cached
    h1 = df.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"},
    ).dropna()
    _h1_memo[key] = h1
    return h1


def cached_ema20_h1(h1: pd.DataFrame) -> pd.Series:
    """Return the EMA-20 series for an H1 DataFrame, memoized per instance.

    Avoids recomputing the full EWM series on every per-signal param call
    when multiple params share the same H1 DataFrame.
    """
    key = id(h1)
    cached = _ema20_h1_memo.get(key)
    if cached is not None:
        return cached
    ema = h1["close"].ewm(span=20, adjust=False).mean()
    _ema20_h1_memo[key] = ema
    return ema


def cached_d1(df: pd.DataFrame) -> pd.DataFrame:
    """Return the broker-day D1 resample of ``df``, memoized per instance."""
    key = id(df)
    cached = _d1_memo.get(key)
    if cached is not None:
        return cached
    broker = df.tz_convert(EXCHANGE_TZ)
    d1 = broker.resample("1D").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"},
    ).dropna().tz_convert("UTC")
    _d1_memo[key] = d1
    return d1
