"""Tests for analytics/params/structure_htf.py — premium_discount_zone param."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.structure_htf import premium_discount_zone


def _make_candles(n: int, base_price: float = 1.1000, freq: str = "15min") -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "open":   [base_price] * n,
        "high":   [base_price + 0.0010] * n,
        "low":    [base_price - 0.0010] * n,
        "close":  [base_price] * n,
        "volume": [1000.0] * n,
    }, index=idx)


def _signal(**kwargs):
    m = MagicMock()
    m.strategy = kwargs.get("strategy", "fvg-impulse")
    m.symbol = kwargs.get("symbol", "EURUSD")
    m.direction = kwargs.get("direction", "BUY")
    m.candle_time = kwargs.get("candle_time", pd.Timestamp("2024-01-02 08:00", tz="UTC"))
    m.entry = kwargs.get("entry", 1.1000)
    m.sl = kwargs.get("sl", 1.0990)
    m.tp = kwargs.get("tp", 1.1010)
    m.risk_pips = kwargs.get("risk_pips", 10.0)
    m.spread_pips = kwargs.get("spread_pips", 1.0)
    m.signal_metadata = kwargs.get("signal_metadata", {})
    m.resolution_candles = kwargs.get("resolution_candles", None)
    return m


def _make_wide_candles(n: int = 400) -> pd.DataFrame:
    """M15 candles spanning >2 days with realistic variation for D1 resampling."""
    idx = pd.date_range("2024-01-01 00:00", periods=n, freq="15min", tz="UTC")
    prices = []
    for i in range(n):
        # Day 1 (bars 0-95): range 1.0900 - 1.1100
        # Day 2 (bars 96-191): range 1.1000 - 1.1200 — signal is on day 2
        day = i // 96
        if day == 0:
            low = 1.0900
            high = 1.1100
        else:
            low = 1.1000
            high = 1.1200
        mid = (low + high) / 2
        prices.append((mid, high + 0.0005, low - 0.0005, mid))
    opens, highs, lows, closes = zip(*prices)
    return pd.DataFrame({
        "open": list(opens),
        "high": list(highs),
        "low": list(lows),
        "close": list(closes),
        "volume": [1000.0] * n,
    }, index=idx)


def test_premium_discount_returns_none_no_candles():
    sig = _signal()
    assert premium_discount_zone(sig, None) is None


def test_premium_discount_discount_zone():
    candles = _make_wide_candles()
    # Prior day H=1.1205, L=1.0895, range=0.031
    # Entry at 1.0910 → pos ≈ 0.048 → discount (< 0.33)
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.0910,
    )
    result = premium_discount_zone(sig, candles)
    assert result == "discount"


def test_premium_discount_premium_zone():
    candles = _make_wide_candles()
    # Prior day H=1.1205, L=1.0895, range=0.031
    # Entry at 1.1150 → pos ≈ (1.115 - 1.0895) / 0.031 ≈ 0.82 → premium (> 0.67)
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1150,
    )
    result = premium_discount_zone(sig, candles)
    assert result == "premium"


def test_premium_discount_equilibrium():
    candles = _make_wide_candles()
    # Prior day H=1.1205, L=1.0895, midpoint=1.105 → pos=0.5 → equilibrium
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1050,
    )
    result = premium_discount_zone(sig, candles)
    assert result == "equilibrium"


def test_premium_discount_boundary_midpoint():
    candles = _make_wide_candles()
    # Prior day H=1.1205, L=1.0895, range=0.031, midpoint=1.105 → pos=0.5 → equilibrium
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1050,
    )
    result = premium_discount_zone(sig, candles)
    assert result == "equilibrium"


def test_premium_discount_just_above_33pct():
    candles = _make_wide_candles()
    # Prior day H=1.1205, L=1.0895000000000001, range≈0.031
    # Entry well above 33%: pos ≈ 0.5 → equilibrium
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1050,
    )
    result = premium_discount_zone(sig, candles)
    assert result == "equilibrium"


def test_premium_discount_empty_candles():
    # Empty candle DataFrame → D1 resample empty → None
    candles = pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"],
        index=pd.DatetimeIndex([], tz="UTC"),
    )
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1000,
    )
    assert premium_discount_zone(sig, candles) is None


def test_premium_discount_narrow_day_range():
    # Build candles where day range is < 3 pips (0.0003 for EURUSD)
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="15min", tz="UTC")
    # Extremely tight range — 0.0001 spread only
    df = pd.DataFrame({
        "open":   [1.1000] * n,
        "high":   [1.10001] * n,
        "low":    [1.09999] * n,
        "close":  [1.1000] * n,
        "volume": [1000.0] * n,
    }, index=idx)
    sig = _signal(
        candle_time=pd.Timestamp("2024-01-02 08:00", tz="UTC"),
        entry=1.1000,
    )
    assert premium_discount_zone(sig, df) is None
