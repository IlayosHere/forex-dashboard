"""
tests/test_volume_params.py
---------------------------
Unit tests for ``analytics.params.volume.volume_regime``.

The original ``relative_volume`` and ``volume_percentile`` params were removed
in analytics phase 5. This file now covers ``volume_regime`` only.
For the session-normalisation behaviour see
``tests/test_analytics_volume_regime_v2.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from analytics.params.volume import volume_regime


def _make_candles(
    n: int = 60,
    base_price: float = 1.08,
    volume: float | list[float] | None = 100.0,
) -> pd.DataFrame:
    """Build a deterministic M15 OHLC DataFrame with an optional volume column."""
    idx = pd.date_range(
        "2025-03-10 14:00", periods=n, freq="15min", tz="UTC",
    )
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
        assert len(volume) == n, "volume list must match candle count"
        df["volume"] = volume
    else:
        df["volume"] = [float(volume)] * n
    return df


def _signal(
    *,
    candle_time: datetime | None = None,
    symbol: str = "EURUSD",
    direction: str = "BUY",
    risk_pips: float = 10.0,
    spread_pips: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> MagicMock:
    sig = MagicMock()
    sig.candle_time = candle_time or datetime(
        2025, 3, 10, 16, 0, tzinfo=timezone.utc,
    )
    sig.symbol = symbol
    sig.direction = direction
    sig.risk_pips = risk_pips
    sig.spread_pips = spread_pips
    sig.signal_metadata = metadata or {}
    return sig


# ---------------------------------------------------------------------------
# volume_regime — bucket thresholds
# ---------------------------------------------------------------------------

def test_volume_regime_low() -> None:
    vols = [100.0] * 60
    vols[59] = 50.0  # 0.5× mean → low
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    assert volume_regime(sig, df) == "low"


def test_volume_regime_normal() -> None:
    df = _make_candles(n=60, volume=100.0)
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    assert volume_regime(sig, df) == "normal"


def test_volume_regime_high() -> None:
    vols = [100.0] * 60
    vols[59] = 200.0  # 2.0× mean → high
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    assert volume_regime(sig, df) == "high"


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------

def test_volume_regime_returns_none_when_column_missing() -> None:
    df = _make_candles(n=60, volume=None)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert volume_regime(sig, df) is None


def test_volume_params_return_none_without_candles() -> None:
    sig = _signal()
    assert volume_regime(sig, None) is None


def test_volume_regime_returns_none_when_bar_volume_is_nan() -> None:
    vols = [100.0] * 60
    df = _make_candles(n=60, volume=vols)
    df.loc[df.index[59], "volume"] = np.nan
    sig = _signal(candle_time=df.index[59].to_pydatetime())
    assert volume_regime(sig, df) is None
