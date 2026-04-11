"""
tests/test_volume_params.py
---------------------------
Unit tests for the tick-count volume parameters exposed by
``analytics.params.candle_derived``: ``relative_volume``,
``volume_percentile``, and ``volume_regime``.

Volume here is TradingView tick count (activity proxy), not traded lot
volume — FX has no central exchange. These tests exercise both the
happy paths and the graceful-degradation paths the analytics pipeline
relies on when a pair/timeframe returns no volume column.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from analytics.params.candle_derived import (
    relative_volume,
    volume_percentile,
    volume_regime,
)


def _make_candles(
    n: int = 60,
    base_price: float = 1.08,
    volume: float | list[float] | None = 100.0,
) -> pd.DataFrame:
    """Build a deterministic M15 OHLC DataFrame with an optional volume column.

    Parameters
    ----------
    n : int
        Number of bars.
    base_price : float
        Starting price for the monotonically rising series.
    volume : float | list[float] | None
        - ``None``: omit the volume column entirely.
        - ``float``: constant volume across every bar.
        - ``list[float]``: explicit per-bar volume (must have length ``n``).
    """
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
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
        2025, 3, 10, 6, 0, tzinfo=timezone.utc,
    )
    sig.symbol = symbol
    sig.direction = direction
    sig.risk_pips = risk_pips
    sig.spread_pips = spread_pips
    sig.signal_metadata = metadata or {}
    return sig


# ---------------------------------------------------------------------------
# relative_volume — happy paths
# ---------------------------------------------------------------------------


def test_relative_volume_equals_one_when_constant_volume() -> None:
    df = _make_candles(n=60, volume=100.0)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    result = relative_volume(sig, df)
    assert result is not None
    assert result == 1.0


def test_relative_volume_above_one_when_signal_bar_spikes() -> None:
    vols = [100.0] * 60
    vols[25] = 500.0
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    result = relative_volume(sig, df)
    assert result is not None
    assert result == 5.0


def test_relative_volume_below_one_when_signal_bar_dips() -> None:
    vols = [200.0] * 60
    vols[25] = 50.0
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    result = relative_volume(sig, df)
    assert result is not None
    assert result == 0.25


# ---------------------------------------------------------------------------
# volume_percentile — happy paths
# ---------------------------------------------------------------------------


def test_volume_percentile_max_when_signal_bar_is_largest() -> None:
    # 50-bar window ending at index 49; set bar 49 as the largest.
    vols = [100.0] * 60
    vols[49] = 500.0
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[49].to_pydatetime())
    result = volume_percentile(sig, df)
    assert result is not None
    assert result == 100.0


def test_volume_percentile_min_when_signal_bar_is_smallest() -> None:
    # 50-bar window ending at index 49; make bar 49 the strict minimum.
    vols = [100.0] * 60
    vols[49] = 10.0
    df = _make_candles(n=60, volume=vols)
    sig = _signal(candle_time=df.index[49].to_pydatetime())
    result = volume_percentile(sig, df)
    assert result is not None
    assert result == 2.0


# ---------------------------------------------------------------------------
# volume_regime — bucket thresholds
# ---------------------------------------------------------------------------


def _regime_df_for_ratio(ratio: float) -> pd.DataFrame:
    """Build a DataFrame where relative_volume at bar 25 equals ``ratio``."""
    baseline = 100.0
    bar_vol = baseline * ratio
    vols = [baseline] * 60
    vols[25] = bar_vol
    return _make_candles(n=60, volume=vols)


def test_volume_regime_low() -> None:
    df = _regime_df_for_ratio(0.5)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert volume_regime(sig, df) == "low"


def test_volume_regime_normal() -> None:
    df = _regime_df_for_ratio(1.0)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert volume_regime(sig, df) == "normal"


def test_volume_regime_high() -> None:
    df = _regime_df_for_ratio(2.0)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert volume_regime(sig, df) == "high"


# ---------------------------------------------------------------------------
# Graceful degradation — must return None, never raise
# ---------------------------------------------------------------------------


def test_relative_volume_returns_none_when_column_missing() -> None:
    df = _make_candles(n=60, volume=None)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert relative_volume(sig, df) is None
    assert volume_percentile(sig, df) is None
    assert volume_regime(sig, df) is None


def test_volume_percentile_returns_none_with_insufficient_history() -> None:
    df = _make_candles(n=30, volume=100.0)
    sig = _signal(candle_time=df.index[29].to_pydatetime())
    assert volume_percentile(sig, df) is None


def test_relative_volume_returns_none_with_insufficient_history() -> None:
    df = _make_candles(n=60, volume=100.0)
    sig = _signal(candle_time=df.index[5].to_pydatetime())
    assert relative_volume(sig, df) is None


def test_volume_params_return_none_without_candles() -> None:
    sig = _signal()
    assert relative_volume(sig, None) is None
    assert volume_percentile(sig, None) is None
    assert volume_regime(sig, None) is None


def test_volume_regime_returns_none_when_relative_volume_none() -> None:
    df = _make_candles(n=60, volume=None)
    sig = _signal(candle_time=df.index[25].to_pydatetime())
    assert volume_regime(sig, df) is None


def test_volume_params_return_none_when_bar_volume_is_nan() -> None:
    vols = [100.0] * 60
    df = _make_candles(n=60, volume=vols)
    df.loc[df.index[49], "volume"] = np.nan
    sig = _signal(candle_time=df.index[49].to_pydatetime())
    assert relative_volume(sig, df) is None
    assert volume_percentile(sig, df) is None
    assert volume_regime(sig, df) is None
