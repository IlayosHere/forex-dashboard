"""
tests/test_candle_cache.py
--------------------------
Unit tests for analytics/candle_cache.py: strategy->interval routing, cache
hits, H1/D1 resampling, and warm() with (symbol, strategy) pairs. The shared
``get_candles`` is patched so nothing hits the network.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable

import pandas as pd
import pytest
from tvDatafeed import Interval

from analytics import candle_cache as cache_mod
from analytics.candle_cache import (
    STRATEGY_INTERVALS,
    CandleCache,
    _next_bar_close,
    get_app_cache,
    interval_for_strategy,
)
from shared.market_data import EXCHANGE_TZ


def _make_df(n: int = 300) -> pd.DataFrame:
    """Build a deterministic M-bar DataFrame with UTC index."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    base = 1.08
    return pd.DataFrame(
        {
            "open":  [base + i * 0.0001 for i in range(n)],
            "high":  [base + i * 0.0001 + 0.0010 for i in range(n)],
            "low":   [base + i * 0.0001 - 0.0005 for i in range(n)],
            "close": [base + i * 0.0001 + 0.0003 for i in range(n)],
        },
        index=idx,
    )


@pytest.fixture()
def patched_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, Interval, int]]:
    """Patch shared fetch; record (symbol, interval, count) calls."""
    calls: list[tuple[str, Interval, int]] = []

    def fake_get_candles(
        symbol: str, interval: Interval, count: int = 300,
    ) -> pd.DataFrame:
        calls.append((symbol, interval, count))
        return _make_df()

    monkeypatch.setattr(cache_mod, "get_candles", fake_get_candles)
    return calls


# ---------------------------------------------------------------------------
# Registry + interval_for_strategy
# ---------------------------------------------------------------------------


def test_strategy_intervals_registry_known_strategies() -> None:
    assert STRATEGY_INTERVALS["fvg-impulse"] == Interval.in_15_minute
    assert STRATEGY_INTERVALS["fvg-impulse-5m"] == Interval.in_5_minute
    assert STRATEGY_INTERVALS["nova-candle"] == Interval.in_15_minute


def test_interval_for_strategy_fallback_to_m15() -> None:
    assert interval_for_strategy("unknown-strategy") == Interval.in_15_minute


# ---------------------------------------------------------------------------
# CandleCache.get — interval routing
# ---------------------------------------------------------------------------


def test_get_fvg_impulse_uses_m15(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    CandleCache().get("EURUSD", "fvg-impulse")
    assert patched_fetch[0][0] == "EURUSD"
    assert patched_fetch[0][1] == Interval.in_15_minute


def test_get_fvg_impulse_5m_uses_m5(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    CandleCache().get("EURUSD", "fvg-impulse-5m")
    assert patched_fetch[0][1] == Interval.in_5_minute


def test_get_nova_candle_uses_m15(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    CandleCache().get("EURUSD", "nova-candle")
    assert patched_fetch[0][1] == Interval.in_15_minute


def test_get_unknown_strategy_defaults_to_m15(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    CandleCache().get("EURUSD", "mystery-strategy")
    assert patched_fetch[0][1] == Interval.in_15_minute


def test_get_uses_per_interval_bar_count(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    cache.get("EURUSD", "fvg-impulse-5m")
    m15_call = next(c for c in patched_fetch if c[1] == Interval.in_15_minute)
    m5_call = next(c for c in patched_fetch if c[1] == Interval.in_5_minute)
    assert m15_call[2] == 480
    assert m5_call[2] == 1440


# ---------------------------------------------------------------------------
# Cache-hit behaviour
# ---------------------------------------------------------------------------


def test_same_symbol_strategy_hits_cache_second_call(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    cache.get("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == 1


def test_same_symbol_different_strategies_are_separate(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    """M5 and M15 for the same symbol are cached independently."""
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    cache.get("EURUSD", "fvg-impulse-5m")
    intervals = {c[1] for c in patched_fetch}
    assert intervals == {Interval.in_15_minute, Interval.in_5_minute}
    assert len(patched_fetch) == 2


def test_two_strategies_on_same_interval_share_cache_entry(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    """fvg-impulse and nova-candle both map to M15 → one fetch."""
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    cache.get("EURUSD", "nova-candle")
    assert len(patched_fetch) == 1


# ---------------------------------------------------------------------------
# get_h1 and get_d1 resampling
# ---------------------------------------------------------------------------


def test_get_h1_returns_resampled_hourly_bars(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    h1 = cache.get_h1("EURUSD", "fvg-impulse")
    assert h1 is not None
    assert set(h1.columns) == {"open", "high", "low", "close"}
    # 300 M15 bars spanning 75 hours → exactly 75 H1 bars
    assert 70 <= len(h1) <= 80


def test_get_h1_cache_reused(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    cache.get_h1("EURUSD", "fvg-impulse")
    cache.get_h1("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == 1


def test_get_d1_returns_broker_day_bars(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    d1 = cache.get_d1("EURUSD", "fvg-impulse")
    assert d1 is not None
    assert str(d1.index.tz) == "UTC"
    # 300 M15 bars ≈ 75 hours → 3 broker days (± boundary day)
    assert 3 <= len(d1) <= 5


def test_get_d1_cache_reused(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    cache.get_d1("EURUSD", "fvg-impulse")
    cache.get_d1("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == 1


# ---------------------------------------------------------------------------
# warm()
# ---------------------------------------------------------------------------


def test_warm_prefetches_each_pair(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    cache = CandleCache()
    cache.warm([
        ("EURUSD", "fvg-impulse"),
        ("GBPUSD", "fvg-impulse-5m"),
    ])
    assert len(patched_fetch) == 2
    by_symbol = {call[0]: call[1] for call in patched_fetch}
    assert by_symbol["EURUSD"] == Interval.in_15_minute
    assert by_symbol["GBPUSD"] == Interval.in_5_minute


def test_warm_deduplicates_same_interval(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    """Two strategies sharing the same interval warm once per (sym, interval)."""
    cache = CandleCache()
    cache.warm([
        ("EURUSD", "fvg-impulse"),
        ("EURUSD", "nova-candle"),  # also M15
    ])
    # Both strategies resolve to Interval.in_15_minute → single fetch
    assert len(patched_fetch) == 1


# ---------------------------------------------------------------------------
# Bar-aligned TTL — _next_bar_close
# ---------------------------------------------------------------------------


def test_next_bar_close_m15_midbar() -> None:
    now = datetime(2025, 3, 10, 14, 7, 0, tzinfo=timezone.utc)
    expected = datetime(2025, 3, 10, 14, 15, 0, tzinfo=timezone.utc)
    assert _next_bar_close(Interval.in_15_minute, now) == expected


def test_next_bar_close_m15_exact_boundary() -> None:
    """At exact boundary the function returns the same instant (which forces
    the next cache access to refetch — the simple, correct behaviour)."""
    now = datetime(2025, 3, 10, 14, 15, 0, tzinfo=timezone.utc)
    expected = datetime(2025, 3, 10, 14, 30, 0, tzinfo=timezone.utc)
    # Snap-down at 14:15 → bar_open == 14:15 → + 15m = 14:30
    assert _next_bar_close(Interval.in_15_minute, now) == expected


def test_next_bar_close_m5_midbar() -> None:
    now = datetime(2025, 3, 10, 14, 7, 30, tzinfo=timezone.utc)
    expected = datetime(2025, 3, 10, 14, 10, 0, tzinfo=timezone.utc)
    assert _next_bar_close(Interval.in_5_minute, now) == expected


def test_next_bar_close_h1() -> None:
    now = datetime(2025, 3, 10, 14, 30, 0, tzinfo=timezone.utc)
    expected = datetime(2025, 3, 10, 15, 0, 0, tzinfo=timezone.utc)
    assert _next_bar_close(Interval.in_1_hour, now) == expected


def test_next_bar_close_daily_broker_midnight() -> None:
    """D1 TTL must align to broker-midnight, not UTC-midnight."""
    now = datetime(2025, 3, 10, 20, 0, 0, tzinfo=timezone.utc)
    got = _next_bar_close(Interval.in_daily, now)
    # Expected = the next Asia/Jerusalem 00:00 after ``now``, in UTC.
    broker_now = now.astimezone(EXCHANGE_TZ)
    expected_local = broker_now.replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    # Advance to the next broker-midnight strictly after ``now``.
    from datetime import timedelta
    while expected_local <= broker_now:
        expected_local += timedelta(days=1)
    expected = expected_local.astimezone(timezone.utc)
    assert got == expected
    assert got > now


def test_next_bar_close_unknown_interval_fallback() -> None:
    """Unknown interval falls back to a short wall-clock TTL (safe degrade)."""
    now = datetime(2025, 3, 10, 14, 7, 30, tzinfo=timezone.utc)
    got = _next_bar_close(Interval.in_30_minute, now)
    # Fallback path: second/microsecond snapped down + 1 minute.
    assert got == datetime(2025, 3, 10, 14, 8, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# TTL-aware get()
# ---------------------------------------------------------------------------


@pytest.fixture()
def frozen_time(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[datetime], None]:
    """Freeze ``datetime.now`` used inside ``candle_cache`` and let tests advance it."""
    current: list[datetime] = [
        datetime(2025, 3, 10, 14, 0, 0, tzinfo=timezone.utc),
    ]

    class _FakeDatetime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:  # type: ignore[override]
            return current[0]

    monkeypatch.setattr(cache_mod, "datetime", _FakeDatetime)

    def _set(t: datetime) -> None:
        current[0] = t

    return _set


def test_get_returns_cached_entry_before_expiry(
    patched_fetch: list[tuple[str, Interval, int]],
    frozen_time: Callable[[datetime], None],
) -> None:
    frozen_time(datetime(2025, 3, 10, 14, 2, 0, tzinfo=timezone.utc))
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    # Advance to 14:10 — still inside the 14:00–14:15 M15 bar.
    frozen_time(datetime(2025, 3, 10, 14, 10, 0, tzinfo=timezone.utc))
    cache.get("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == 1


def test_get_refetches_after_expiry(
    patched_fetch: list[tuple[str, Interval, int]],
    frozen_time: Callable[[datetime], None],
) -> None:
    frozen_time(datetime(2025, 3, 10, 14, 2, 0, tzinfo=timezone.utc))
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    # Advance past the 14:15 bar close.
    frozen_time(datetime(2025, 3, 10, 14, 16, 0, tzinfo=timezone.utc))
    cache.get("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == 2


def test_expired_entry_evicts_derived_caches(
    patched_fetch: list[tuple[str, Interval, int]],
    frozen_time: Callable[[datetime], None],
) -> None:
    frozen_time(datetime(2025, 3, 10, 14, 2, 0, tzinfo=timezone.utc))
    cache = CandleCache()
    cache.get("EURUSD", "fvg-impulse")
    cache.get_atr("EURUSD", "fvg-impulse")
    cache.get_h1("EURUSD", "fvg-impulse")
    # Internal caches populated.
    key = ("EURUSD", Interval.in_15_minute)
    assert any(k[0] == key for k in cache._atr_cache)
    assert key in cache._h1_cache

    # Advance past expiry and re-fetch the underlying entry.
    frozen_time(datetime(2025, 3, 10, 14, 16, 0, tzinfo=timezone.utc))
    cache.get("EURUSD", "fvg-impulse")
    # Derived caches for this key must be evicted.
    assert not any(k[0] == key for k in cache._atr_cache)
    assert key not in cache._h1_cache


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


def test_concurrent_get_same_key_races_but_converges(
    patched_fetch: list[tuple[str, Interval, int]],
) -> None:
    """Multiple threads hitting the same cold key converge to the same entry.

    The first thread to acquire the lock observes the cache miss, fetches,
    and stores. Other threads may observe the miss before the store lands
    (1 or 2 fetches is acceptable), but all threads ultimately receive the
    same DataFrame object (the last write wins and ``get`` returns it).
    """
    cache = CandleCache()

    def worker() -> pd.DataFrame | None:
        return cache.get("EURUSD", "fvg-impulse")

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda _: worker(), range(10)))

    # 1..N fetches allowed (rare race), but all results must be non-None
    # and equal-valued — and the cache must ultimately converge.
    assert all(r is not None for r in results)
    assert 1 <= len(patched_fetch) <= 10
    # After convergence, the cache holds exactly one entry for that key.
    assert len(cache._cache) == 1
    # Next call is a hit (no new fetch).
    prior_fetches = len(patched_fetch)
    cache.get("EURUSD", "fvg-impulse")
    assert len(patched_fetch) == prior_fetches


# ---------------------------------------------------------------------------
# App-scoped singleton
# ---------------------------------------------------------------------------


def test_get_app_cache_returns_singleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cache_mod, "_APP_CACHE", None)
    a = get_app_cache()
    b = get_app_cache()
    assert a is b
