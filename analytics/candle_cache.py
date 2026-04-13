"""Timeframe-aware in-memory cache for candle data (``CandleCache`` + app singleton).

``STRATEGY_INTERVALS`` is the single source of truth for strategy → timeframe.
Bar-aligned TTL: each entry expires at the close of the current bar.
Derived series helpers live in ``analytics.candle_helpers`` (re-exported here).
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import pandas as pd
from tvDatafeed import Interval

from shared.market_data import EXCHANGE_TZ, get_candles
from analytics.candle_helpers import (
    cached_atr,
    cached_d1,
    cached_ema20_h1,
    cached_h1,
    clear_memos,
    get_candles_around,
)

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


def next_bar_close(interval: Interval, now: datetime) -> datetime:
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
        self._lock = threading.Lock()
        # Single-flight: maps a key to an Event that the in-progress fetch will
        # set when done.  Any other thread that races in during the fetch waits
        # on this event instead of issuing a duplicate network call.
        self._inflight: dict[CacheKey, threading.Event] = {}

    def get(
        self, symbol: str, strategy: str,
    ) -> pd.DataFrame | None:
        """Return cached candles for a (symbol, strategy), fetching on miss or expiry.

        Uses a single-flight guard so concurrent callers for the same key share
        one network fetch rather than each issuing their own, which avoids
        duplicate requests to tvDatafeed and eliminates the race that could
        produce an error on the first analytics load.
        """
        interval = interval_for_strategy(strategy)
        key: CacheKey = (symbol, interval)

        while True:
            now = datetime.now(timezone.utc)  # refresh on every iteration (incl. after wait)
            with self._lock:
                entry = self._cache.get(key)
                if entry is not None and now < entry.expires_at:
                    return entry.df

                # Another thread is already fetching this key — grab its event
                # and wait outside the lock so we don't block other keys.
                if key in self._inflight:
                    event = self._inflight[key]
                else:
                    # We are the designated fetcher for this key.
                    event = threading.Event()
                    self._inflight[key] = event
                    break  # proceed to fetch below

            # Wait for the in-progress fetch to finish, then re-check the cache.
            # timeout=30 prevents an indefinite hang if the fetcher thread is
            # killed before reaching its finally block (e.g. KeyboardInterrupt).
            event.wait(timeout=30)

        # We are the designated fetcher — perform network I/O outside the lock.
        try:
            df = self._fetch(symbol, interval)
            # Capture time AFTER the fetch so the bar-aligned TTL is computed
            # from the actual completion time, not the pre-fetch timestamp.
            expires_at = next_bar_close(interval, datetime.now(timezone.utc))
            with self._lock:
                self._cache[key] = _CacheEntry(df=df, expires_at=expires_at)
            return df
        finally:
            with self._lock:
                self._inflight.pop(key, None)
            event.set()  # wake all waiters regardless of success or exception

    def warm(
        self, pairs: list[tuple[str, str]],
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """Pre-fetch candles for a list of (symbol, strategy) pairs in parallel.

        Already-valid cache entries are skipped immediately. Missing or expired
        entries are fetched concurrently (one thread per pair, up to 8). This
        reduces cold-cache time from N × fetch_duration to ~1 × fetch_duration.

        Returns ``(warmed, failed)`` — pairs that succeeded vs. those where
        the fetch returned ``None``. Failures are handled gracefully by
        ``resolve_all_params`` (candle-dependent params are skipped when
        candles are ``None``).
        """
        if not pairs:
            return [], []

        warmed: list[tuple[str, str]] = []
        failed: list[tuple[str, str]] = []

        # Separate already-cached pairs from those that need a fetch.
        now = datetime.now(timezone.utc)
        to_fetch: list[tuple[str, str]] = []
        for symbol, strategy in pairs:
            key: CacheKey = (symbol, interval_for_strategy(strategy))
            with self._lock:
                entry = self._cache.get(key)
            if entry is not None and now < entry.expires_at:
                warmed.append((symbol, strategy))
            else:
                to_fetch.append((symbol, strategy))

        if not to_fetch:
            return warmed, failed

        # Fetch missing pairs in parallel. self.get() already performs network
        # I/O outside the lock, so concurrent calls for different keys are safe.
        # Cap at 4 threads — the global _tv_semaphore in market_data limits
        # actual concurrent TradingView requests to 2 regardless, so extra
        # threads beyond that just queue inside the semaphore without benefit.
        with ThreadPoolExecutor(max_workers=min(len(to_fetch), 4)) as pool:
            future_to_pair = {
                pool.submit(self.get, sym, strat): (sym, strat)
                for sym, strat in to_fetch
            }
            for future in as_completed(future_to_pair):
                pair = future_to_pair[future]
                try:
                    df = future.result()
                    (warmed if df is not None else failed).append(pair)
                except Exception:
                    logger.exception("Unexpected error warming %s/%s", *pair)
                    failed.append(pair)

        return warmed, failed

    def clear(self) -> None:
        """Clear all caches. In-flight fetches are not interrupted."""
        with self._lock:
            self._cache.clear()
        clear_memos()

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

_app_cache: CandleCache | None = None
_app_cache_lock = threading.Lock()


def get_app_cache() -> CandleCache:
    """Return the process-wide singleton ``CandleCache``.

    Intended as a FastAPI ``Depends`` target for the analytics routes.
    Uses an explicit module-level variable so tests can reset the singleton
    by assigning ``cache_mod._app_cache = None``.
    """
    global _app_cache
    if _app_cache is not None:
        return _app_cache
    with _app_cache_lock:
        if _app_cache is None:
            _app_cache = CandleCache()
    return _app_cache
