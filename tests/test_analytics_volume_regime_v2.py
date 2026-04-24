"""
tests/test_analytics_volume_regime_v2.py
-----------------------------------------
Tests for the session-normalised ``volume_regime`` parameter.

The new implementation compares signal-bar volume only against prior bars
that fall in the same session window (Asian / London / NY) so that the
natural session-volume difference does not dominate the bucket assignment.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pandas as pd

from analytics.params.volume import volume_regime


def _make_candles(
    n: int = 60,
    base_price: float = 1.08,
    volume: float | list[float] | None = 100.0,
    freq: str = "15min",
    start: str = "2025-03-10 14:00",
) -> pd.DataFrame:
    """Build a deterministic OHLC DataFrame with an optional volume column."""
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    data: dict[str, list[float]] = {
        "open": [base_price + i * 0.0001 for i in range(n)],
        "high": [base_price + i * 0.0001 + 0.0010 for i in range(n)],
        "low": [base_price + i * 0.0001 - 0.0005 for i in range(n)],
        "close": [base_price + i * 0.0001 + 0.0003 for i in range(n)],
    }
    df = pd.DataFrame(data, index=idx)
    if volume is None:
        return df
    if isinstance(volume, list):
        assert len(volume) == n
        df["volume"] = volume
    else:
        df["volume"] = [float(volume)] * n
    return df


def _signal(
    candle_time: datetime,
    symbol: str = "EURUSD",
    direction: str = "BUY",
) -> MagicMock:
    sig = MagicMock()
    sig.candle_time = candle_time
    sig.symbol = symbol
    sig.direction = direction
    sig.risk_pips = 10.0
    sig.spread_pips = 0.5
    sig.signal_metadata = {}
    return sig


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_volume_regime_high_in_same_session() -> None:
    """NY-session signal with bar volume 2× session mean → 'high'."""
    # Start at 14:00 UTC (10:00 NY) — firmly in the NY session.
    # 60 bars × 15 min, all at volume=100 except the last bar = 200.
    vols = [100.0] * 60
    vols[59] = 200.0
    df = _make_candles(n=60, volume=vols, start="2025-03-10 14:00")
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    result = volume_regime(sig, df)
    assert result == "high"


def test_volume_regime_low_volume() -> None:
    """NY-session signal with bar volume 0.5× session mean → 'low'."""
    vols = [100.0] * 60
    vols[59] = 50.0
    df = _make_candles(n=60, volume=vols, start="2025-03-10 14:00")
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    result = volume_regime(sig, df)
    assert result == "low"


def test_volume_regime_normal_volume() -> None:
    """Constant volume across all bars → 'normal' (rv == 1.0)."""
    df = _make_candles(n=60, volume=100.0, start="2025-03-10 14:00")
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    result = volume_regime(sig, df)
    assert result == "normal"


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

def test_volume_regime_no_volume_column() -> None:
    """Candles without a volume column → None."""
    df = _make_candles(n=60, volume=None, start="2025-03-10 14:00")
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    assert volume_regime(sig, df) is None


def test_volume_regime_none_when_no_candles() -> None:
    """candles=None → None."""
    sig = _signal(candle_time=datetime(2025, 3, 10, 15, 0, tzinfo=timezone.utc))
    assert volume_regime(sig, None) is None


# ---------------------------------------------------------------------------
# Session fallback
# ---------------------------------------------------------------------------

def test_volume_regime_falls_back_when_few_session_bars() -> None:
    """Fewer than 10 same-session bars in prior 50 → falls back to all 50 bars.

    We build 61 bars: the first 60 are in the NY session (14:00–23:45 UTC),
    the last bar is placed 15 min after the 60th so it's also in NY session
    but we then relabel all prior bars to a non-overlapping Asian start time
    in a way that produces a unique index.

    Simpler approach: build two separate DataFrames.
    - 60 NY-session bars (volume=100).
    - 1 Asian bar appended (volume=200) — represents the signal bar.
    Since Asian and NY don't overlap hourly, the prior 50 bars will all be
    NY-session, leaving <10 Asian bars → fallback triggers.
    Result: rv = 200 / 100 = 2.0 → 'high'.
    """
    # 50 NY-session bars at 15-min intervals starting 14:00 UTC.
    ny_start = pd.date_range("2025-03-10 14:00", periods=50, freq="15min", tz="UTC")
    base = 1.08
    ny_df = pd.DataFrame(
        {
            "open": [base] * 50,
            "high": [base + 0.001] * 50,
            "low": [base - 0.0005] * 50,
            "close": [base + 0.0003] * 50,
            "volume": [100.0] * 50,
        },
        index=ny_start,
    )
    # 1 Asian-session bar: 03:00 UTC next day (22:00 NY = Asian bucket).
    asian_time = pd.Timestamp("2025-03-11 03:00", tz="UTC")
    asian_df = pd.DataFrame(
        {
            "open": [base],
            "high": [base + 0.001],
            "low": [base - 0.0005],
            "close": [base + 0.0003],
            "volume": [200.0],
        },
        index=pd.DatetimeIndex([asian_time], tz="UTC"),
    )
    df = pd.concat([ny_df, asian_df])
    sig = _signal(candle_time=asian_time.to_pydatetime())
    # Prior 50 bars are all NY-session; 0 Asian bars → fallback to all 50.
    # Signal bar volume=200 vs mean=100 → rv=2.0 → 'high'.
    result = volume_regime(sig, df)
    assert result == "high"
