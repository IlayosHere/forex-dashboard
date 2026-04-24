"""Tests for analytics/params/temporal.py — resolution_candles_param."""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.temporal import resolution_candles_param


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


def test_resolution_candles_happy_path():
    sig = _signal(resolution_candles=12)
    assert resolution_candles_param(sig, None) == 12


def test_resolution_candles_none_when_absent():
    sig = _signal(resolution_candles=None)
    assert resolution_candles_param(sig, None) is None


def test_resolution_candles_returns_int():
    sig = _signal(resolution_candles=5.0)
    result = resolution_candles_param(sig, None)
    assert result == 5
    assert isinstance(result, int)


def test_resolution_candles_zero():
    sig = _signal(resolution_candles=0)
    assert resolution_candles_param(sig, None) == 0


def test_resolution_candles_large_value():
    sig = _signal(resolution_candles=480)
    assert resolution_candles_param(sig, None) == 480


def test_resolution_candles_no_attribute():
    # Signal that doesn't have resolution_candles attribute at all
    sig = MagicMock(spec=["strategy", "symbol", "candle_time", "entry"])
    assert resolution_candles_param(sig, None) is None


def test_resolution_candles_ignores_candles_arg():
    # needs_candles=False — candles arg is always ignored
    sig = _signal(resolution_candles=7)
    assert resolution_candles_param(sig, None) == 7
