"""Tests for analytics/params/liquidity.py — liquidity_swept_prior and sweep_to_signal_bars."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.liquidity import liquidity_swept_prior, sweep_to_signal_bars


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


def _make_sweep_candles(sweep_bar_offset: int, sweep_dir: str, n_total: int = 100) -> pd.DataFrame:
    """Build candles where a sweep occurs at a specific bar offset before the signal bar.

    The signal bar is always the last bar (index n_total - 1).
    sweep_bar_offset: bars before last bar where the sweep happens.
    sweep_dir: "buyside" → bar.high exceeds prior swing high
               "sellside" → bar.low breaks prior swing low.
    """
    base = 1.1000
    highs = [base + 0.0010] * n_total
    lows = [base - 0.0010] * n_total

    signal_idx = n_total - 1
    sweep_idx = signal_idx - sweep_bar_offset

    # outer window is bars (signal_idx - 25) to (signal_idx - 16)
    outer_start = signal_idx - 25
    outer_end = signal_idx - 15  # exclusive
    swing_high = base + 0.0010  # normal high
    swing_low = base - 0.0010   # normal low

    if sweep_dir == "buyside":
        highs[sweep_idx] = swing_high + 0.0050  # exceeds swing high
    else:
        lows[sweep_idx] = swing_low - 0.0050  # breaks swing low

    idx = pd.date_range("2024-01-01", periods=n_total, freq="15min", tz="UTC")
    return pd.DataFrame({
        "open":   [base] * n_total,
        "high":   highs,
        "low":    lows,
        "close":  [base] * n_total,
        "volume": [1000.0] * n_total,
    }, index=idx)


def test_liquidity_swept_prior_returns_none_no_candles():
    sig = _signal()
    assert liquidity_swept_prior(sig, None) is None


def test_sweep_to_signal_bars_returns_none_no_candles():
    sig = _signal()
    assert sweep_to_signal_bars(sig, None) is None


def test_liquidity_swept_prior_no_sweep():
    candles = _make_candles(100)
    sig = _signal(candle_time=candles.index[-1])
    assert liquidity_swept_prior(sig, candles) == "none"


def test_liquidity_swept_prior_buyside_sweep():
    candles = _make_sweep_candles(sweep_bar_offset=5, sweep_dir="buyside")
    sig = _signal(candle_time=candles.index[-1])
    assert liquidity_swept_prior(sig, candles) == "swept_buyside"


def test_liquidity_swept_prior_sellside_sweep():
    candles = _make_sweep_candles(sweep_bar_offset=5, sweep_dir="sellside")
    sig = _signal(candle_time=candles.index[-1])
    assert liquidity_swept_prior(sig, candles) == "swept_sellside"


def test_sweep_to_signal_bars_happy_path():
    candles = _make_sweep_candles(sweep_bar_offset=5, sweep_dir="buyside")
    sig = _signal(candle_time=candles.index[-1])
    result = sweep_to_signal_bars(sig, candles)
    assert result == 5


def test_sweep_to_signal_bars_no_sweep_returns_none():
    candles = _make_candles(100)
    sig = _signal(candle_time=candles.index[-1])
    assert sweep_to_signal_bars(sig, candles) is None


def test_sweep_to_signal_bars_minimum_1():
    # Sweep at bar immediately before signal (offset=1)
    candles = _make_sweep_candles(sweep_bar_offset=1, sweep_dir="sellside")
    sig = _signal(candle_time=candles.index[-1])
    result = sweep_to_signal_bars(sig, candles)
    assert result == 1


def test_liquidity_swept_prior_future_timestamp_returns_none_or_none_sweep():
    # A far-future timestamp: ffill maps to the last bar, outer/lookback windows
    # exist but no prices breach any swing → "none" (no sweep, not a data error).
    candles = _make_candles(100)
    sig = _signal(candle_time=pd.Timestamp("2030-01-01 00:00", tz="UTC"))
    result = liquidity_swept_prior(sig, candles)
    assert result in ("none", None)


def test_liquidity_swept_prior_insufficient_bars():
    # Fewer than _MIN_OUTER (5) bars in outer window → None (can't determine)
    candles = _make_candles(3)
    sig = _signal(candle_time=candles.index[-1])
    # idx=2, outer_end=max(0,2-15)=0, outer_start=0, outer_end<=outer_start → None → "none"
    # With 3 bars idx=2: outer_end=0, outer_start=0, condition 0<=0 → _find_sweep None → None
    assert liquidity_swept_prior(sig, candles) is None
