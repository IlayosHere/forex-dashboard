"""Tests for analytics/params/temporal.py — kill_zone param."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.temporal import kill_zone


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


# UTC 08:00 = NY 03:00 (winter, UTC-5) → asian_kz
_ASIAN_KZ_UTC = pd.Timestamp("2024-01-03 08:00", tz="UTC")
# UTC 10:30 = NY 05:30 → london_kz
_LONDON_KZ_UTC = pd.Timestamp("2024-01-03 10:30", tz="UTC")
# UTC 12:30 = NY 07:30 → ny_am_kz
_NY_AM_KZ_UTC = pd.Timestamp("2024-01-03 12:30", tz="UTC")
# UTC 15:30 = NY 10:30 → ny_lunch
_NY_LUNCH_UTC = pd.Timestamp("2024-01-03 15:30", tz="UTC")
# UTC 18:30 = NY 13:30 → ny_pm_kz
_NY_PM_KZ_UTC = pd.Timestamp("2024-01-03 18:30", tz="UTC")
# UTC 23:00 = NY 18:00 → dead_zone
_DEAD_ZONE_UTC = pd.Timestamp("2024-01-03 23:00", tz="UTC")
# UTC 05:30 = NY 00:30 → dead_zone (midnight)
_DEAD_ZONE_MIDNIGHT_UTC = pd.Timestamp("2024-01-03 05:30", tz="UTC")


def test_kill_zone_asian_kz():
    sig = _signal(candle_time=_ASIAN_KZ_UTC)
    assert kill_zone(sig, None) == "asian_kz"


def test_kill_zone_london_kz():
    sig = _signal(candle_time=_LONDON_KZ_UTC)
    assert kill_zone(sig, None) == "london_kz"


def test_kill_zone_ny_am_kz():
    sig = _signal(candle_time=_NY_AM_KZ_UTC)
    assert kill_zone(sig, None) == "ny_am_kz"


def test_kill_zone_ny_lunch():
    sig = _signal(candle_time=_NY_LUNCH_UTC)
    assert kill_zone(sig, None) == "ny_lunch"


def test_kill_zone_ny_pm_kz():
    sig = _signal(candle_time=_NY_PM_KZ_UTC)
    assert kill_zone(sig, None) == "ny_pm_kz"


def test_kill_zone_dead_zone_evening():
    sig = _signal(candle_time=_DEAD_ZONE_UTC)
    assert kill_zone(sig, None) == "dead_zone"


def test_kill_zone_dead_zone_midnight():
    sig = _signal(candle_time=_DEAD_ZONE_MIDNIGHT_UTC)
    assert kill_zone(sig, None) == "dead_zone"


def test_kill_zone_none_candle_time():
    sig = _signal(candle_time=None)
    # candle_time = None → None return
    assert kill_zone(sig, None) is None


def test_kill_zone_naive_datetime_handled():
    # Naive datetime should be treated as UTC and succeed
    naive_ts = datetime(2024, 1, 3, 12, 30)  # 12:30 naive = NY 07:30 (winter) → ny_am_kz
    sig = _signal(candle_time=naive_ts)
    assert kill_zone(sig, None) == "ny_am_kz"


def test_kill_zone_boundary_ny_am_start():
    # Exactly 07:00 NY → ny_am_kz boundary (UTC 12:00 winter)
    ts = pd.Timestamp("2024-01-03 12:00", tz="UTC")
    sig = _signal(candle_time=ts)
    assert kill_zone(sig, None) == "ny_am_kz"


def test_kill_zone_boundary_london_start():
    # Exactly 05:00 NY → london_kz boundary (UTC 10:00 winter)
    ts = pd.Timestamp("2024-01-03 10:00", tz="UTC")
    sig = _signal(candle_time=ts)
    assert kill_zone(sig, None) == "london_kz"
