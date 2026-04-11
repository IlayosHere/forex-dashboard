"""
analytics/candle_cache.py
-------------------------
Timeframe-aware in-memory caching layer for candle data plus derived series
(ATR, H1 bars, D1 bars).

Each strategy's native timeframe is declared in ``STRATEGY_INTERVALS`` — adding
a new strategy at a new timeframe is a one-line change. The cache keys every
entry by ``(symbol, interval)`` so M5 and M15 fetches for the same symbol are
stored separately.

The cache is **app-scoped** with **bar-aligned TTL**: each entry expires at
the close of the current bar for its timeframe (e.g. an M15 entry fetched
at 14:07 UTC expires at 14:15 UTC). Analytics only cares about closed bars,
so refetching mid-bar is wasted network. Use ``get_app_cache()`` inside a
FastAPI ``Depends`` to obtain the process-wide singleton.

Module-level ``cached_*`` helpers (``cached_atr``, ``cached_h1``, etc.)
provide DataFrame-scoped memoization so derived series are computed once
per underlying DataFrame instance, not once per signal.
"""
from __future__ import annotations

import logging
import threading
import weakref
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import pandas as pd
from tvDatafeed import Interval

from shared.market_data import EXCHANGE_TZ, get_candles

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strategy -> timeframe registry (single source of truth)
# ---------------------------------------------------------------------------
STRATEGY_INTERVALS: dict[str, Interval] = {
    "fvg-impulse":    Interval.in_15_minute,
    "fvg-impulse-5m": Interval.in_5_minute,
    "nova-candle":    Interval.in_15_minute,
}
_DEFAULT_INTERVAL: Interval = Interval.in_15_minute

# Per-interval bar counts sized for HTF-resample needs (H1 EMA-20, D1 ATR-14).
# M5:  1440 bars ≈ 5 days    → ~120 H1 bars, ~5 D1 bars
# M15:  480 bars ≈ 5 days    → ~120 H1 bars, ~5 D1 bars
_BAR_COUNTS: dict[Interval, int] = {
    Interval.in_5_minute:  1440,
    Interval.in_15_minute:  480,
}
_DEFAULT_BAR_COUNT = 480
_DEFAULT_LOOKBACK = 20


def interval_for_strategy(strategy: str) -> Interval:
    """Return the candle timeframe for a strategy, falling back to M15."""
    return STRATEGY_INTERVALS.get(strategy, _DEFAULT_INTERVAL)


def _bar_count_for(interval: Interval) -> int:
    return _BAR_COUNTS.get(interval, _DEFAULT_BAR_COUNT)


# ---------------------------------------------------------------------------
# Bar-aligned TTL
# ---------------------------------------------------------------------------
_INTERVAL_MINUTES: dict[Interval, int] = {
    Interval.in_5_minute:  5,
    Interval.in_15_minute: 15,
    Interval.in_1_hour:    60,
}


def _next_bar_close(interval: Interval, now: datetime) -> datetime:
    """Return the UTC timestamp when the current bar closes."""
    if interval == Interval.in_daily:
        broker_now = now.astimezone(EXCHANGE_TZ)
        next_midnight = (broker_now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        return next_midnight.astimezone(timezone.utc)

    minutes = _INTERVAL_MINUTES.get(interval)
    if minutes is None:
        return now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    total_minutes = now.hour * 60 + now.minute
    bar_open_minutes = (total_minutes // minutes) * minutes
    bar_open = now.replace(
        hour=bar_open_minutes // 60,
        minute=bar_open_minutes % 60,
        second=0,
        microsecond=0,
    )
    return bar_open + timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

CacheKey = tuple[str, Interval]


class _CacheEntry(NamedTuple):
    df: pd.DataFrame | None
    expires_at: datetime


class CandleCache:
    """Thread-safe in-memory cache for candle data, keyed by ``(symbol, interval)``.

    Entries have bar-aligned TTL: each cache miss (or expired entry) triggers
    a fresh fetch, and the expiry is set to the close of the current bar for
    the interval. Derived series (ATR, H1 bars, D1 bars) are evicted when the
    underlying entry expires so they are never computed from stale data.

    The cache is designed to live for the lifetime of the FastAPI app via
    ``get_app_cache()``. Route handlers run on a threadpool, so all mutations
    are guarded by an instance lock. Network I/O (``_fetch``) is performed
    OUTSIDE the lock so concurrent fetches for different keys do not serialize.
    """

    def __init__(self) -> None:
        self._cache: dict[CacheKey, _CacheEntry] = {}
        self._atr_cache: dict[tuple[CacheKey, int], pd.Series] = {}
        self._h1_cache: dict[CacheKey, pd.DataFrame] = {}
        self._d1_cache: dict[CacheKey, pd.DataFrame] = {}
        self._lock = threading.Lock()

    def get(
        self, symbol: str, strategy: str,
    ) -> pd.DataFrame | None:
        """Return cached candles for a (symbol, strategy), fetching on miss or expiry."""
        interval = interval_for_strategy(strategy)
        key: CacheKey = (symbol, interval)
        now = datetime.now(timezone.utc)

        with self._lock:
            entry = self._cache.get(key)
            if entry is not None and now < entry.expires_at:
                return entry.df
            # Expired or missing — evict derived caches keyed off this entry.
            self._atr_cache = {
                k: v for k, v in self._atr_cache.items() if k[0] != key
            }
            self._h1_cache.pop(key, None)
            self._d1_cache.pop(key, None)

        # Fetch outside the lock — network I/O must not serialize other keys.
        df = self._fetch(symbol, interval)
        expires_at = _next_bar_close(interval, now)

        with self._lock:
            self._cache[key] = _CacheEntry(df=df, expires_at=expires_at)
        return df

    def warm(
        self, pairs: list[tuple[str, str]],
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Pre-fetch candles for a list of (symbol, strategy) pairs.

        Returns ``(warmed, failed)`` — pairs that succeeded vs. those where
        the fetch returned ``None``. Failures are handled gracefully by
        ``resolve_all_params`` (candle-dependent params are skipped when
        candles are ``None``).
        """
        warmed: list[tuple[str, str]] = []
        failed: list[tuple[str, str]] = []
        for symbol, strategy in pairs:
            df = self.get(symbol, strategy)
            if df is None:
                failed.append((symbol, strategy))
            else:
                warmed.append((symbol, strategy))
        return warmed, failed

    def clear(self) -> None:
        """Clear all caches."""
        with self._lock:
            self._cache.clear()
            self._atr_cache.clear()
            self._h1_cache.clear()
            self._d1_cache.clear()

    @property
    def cached_keys(self) -> list[CacheKey]:
        """Return the list of cached ``(symbol, interval)`` keys."""
        with self._lock:
            return list(self._cache.keys())

    def _fetch(self, symbol: str, interval: Interval) -> pd.DataFrame | None:
        count = _bar_count_for(interval)
        logger.info("Fetching candle data for %s @ %s (%d bars)", symbol, interval, count)
        return get_candles(symbol, interval, count=count)


# ---------------------------------------------------------------------------
# App-scoped singleton
# ---------------------------------------------------------------------------
_APP_CACHE: CandleCache | None = None


def get_app_cache() -> CandleCache:
    """Return the process-wide singleton ``CandleCache``.

    Intended as a FastAPI ``Depends`` target for the analytics routes.
    The singleton is lazily constructed on first access.
    """
    global _APP_CACHE
    if _APP_CACHE is None:
        _APP_CACHE = CandleCache()
    return _APP_CACHE


# ---------------------------------------------------------------------------
# Backward-compat helper (used by older param modules)
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
# DataFrame-scoped memoization
# ---------------------------------------------------------------------------
# Params receive a ``candles: pd.DataFrame | None`` argument, not a cache.
# To avoid recomputing ATR / H1 / D1 once per signal when many signals share
# the same underlying DataFrame, we memoize derived series in module-level
# WeakValueDictionary keyed by ``id(df)``.
#
# ``CandleCache`` hands the SAME DataFrame object to every signal within a
# single enrichment run, so ``id(df)`` is stable for the duration of a
# request. When the cache expires and re-fetches, a new DataFrame is handed
# out and the old one becomes unreferenced — the WeakValueDictionary entries
# then drop out naturally (no manual eviction needed).

_atr_memo: "weakref.WeakValueDictionary[tuple[int, int], pd.Series]" = (
    weakref.WeakValueDictionary()
)
_h1_memo: "weakref.WeakValueDictionary[int, pd.DataFrame]" = (
    weakref.WeakValueDictionary()
)
_d1_memo: "weakref.WeakValueDictionary[int, pd.DataFrame]" = (
    weakref.WeakValueDictionary()
)
_ema20_h1_memo: "weakref.WeakValueDictionary[int, pd.Series]" = (
    weakref.WeakValueDictionary()
)


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
