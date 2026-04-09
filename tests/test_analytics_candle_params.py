"""
tests/test_analytics_candle_params.py
--------------------------------------
Unit tests for candle-dependent params: candle_derived, fvg_impulse (candle),
and nova_candle (candle). Uses deterministic DataFrame fixtures.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.candle_cache import _compute_atr
from analytics.params.candle_derived import (
    _atr_pips_at_bar,
    _find_signal_bar,
    atr_14,
    risk_pips_atr,
    trend_h1_aligned,
    volatility_percentile,
)
from analytics.params.fvg_impulse import (
    fvg_width_atr_ratio,
    impulse_body_ratio,
    rejection_body_ratio,
    wick_penetration_ratio,
)
from analytics.params.nova_candle import body_atr_ratio, risk_atr_ratio


def _make_candles(n: int = 50, base_price: float = 1.08) -> pd.DataFrame:
    """Build a deterministic M15 OHLC DataFrame."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    data = {
        "open": [base_price + i * 0.0001 for i in range(n)],
        "high": [base_price + i * 0.0001 + 0.0010 for i in range(n)],
        "low": [base_price + i * 0.0001 - 0.0005 for i in range(n)],
        "close": [base_price + i * 0.0001 + 0.0003 for i in range(n)],
    }
    return pd.DataFrame(data, index=idx)


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
# candle_derived.py helpers
# ---------------------------------------------------------------------------


def test_find_signal_bar_exact_match() -> None:
    df = _make_candles()
    sig = _signal(candle_time=df.index[20].to_pydatetime())
    assert _find_signal_bar(df, sig) == 20


def test_find_signal_bar_ffill() -> None:
    """Should find nearest earlier bar when exact time is missing."""
    df = _make_candles()
    # 5 minutes after bar 20 — ffill should land on 20
    t = df.index[20].to_pydatetime() + pd.Timedelta(minutes=5)
    sig = _signal(candle_time=t)
    assert _find_signal_bar(df, sig) == 20


def test_compute_atr_has_correct_length() -> None:
    df = _make_candles(n=30)
    atr = _compute_atr(df, period=14)
    assert len(atr) == 30
    assert pd.isna(atr.iloc[12])  # not enough data yet
    assert not pd.isna(atr.iloc[14])  # enough data from index 13+


def test_atr_pips_at_bar_returns_float() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = _atr_pips_at_bar(df, sig)
    assert result is not None
    assert result > 0


# ---------------------------------------------------------------------------
# candle_derived.py registered params
# ---------------------------------------------------------------------------


def test_atr_14_returns_value() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = atr_14(sig, df)
    assert result is not None
    assert result > 0


def test_atr_14_none_without_candles() -> None:
    assert atr_14(_signal(), None) is None


def test_trend_h1_aligned_returns_bool() -> None:
    # Need enough data for H1 aggregation (24+ H1 bars = 96+ M15 bars)
    df = _make_candles(n=120, base_price=1.08)
    sig = _signal(
        candle_time=df.index[110].to_pydatetime(), direction="BUY",
    )
    result = trend_h1_aligned(sig, df)
    # Data is monotonically rising, so BUY should be aligned
    assert result == True  # noqa: E712 — numpy bool


def test_trend_h1_aligned_none_without_candles() -> None:
    assert trend_h1_aligned(_signal(), None) is None


def test_volatility_percentile_range() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[40].to_pydatetime())
    result = volatility_percentile(sig, df)
    assert result is not None
    assert 0 <= result <= 100


def test_risk_pips_atr_returns_ratio() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime(), risk_pips=15.0)
    result = risk_pips_atr(sig, df)
    assert result is not None
    assert result > 0


# ---------------------------------------------------------------------------
# fvg_impulse.py candle-dependent params
# ---------------------------------------------------------------------------


def test_fvg_width_atr_ratio_returns_value() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata={"fvg_width_pips": 5.0},
    )
    result = fvg_width_atr_ratio(sig, df)
    assert result is not None
    assert result > 0


def test_fvg_width_atr_ratio_none_without_candles() -> None:
    sig = _signal(metadata={"fvg_width_pips": 5.0})
    assert fvg_width_atr_ratio(sig, None) is None


def test_rejection_body_ratio_buy() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
    )
    result = rejection_body_ratio(sig, df)
    assert result is not None
    assert 0 <= result <= 1


def test_wick_penetration_ratio_clamps() -> None:
    df = _make_candles(n=50)
    bar = df.iloc[30]
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        direction="BUY",
        metadata={
            "fvg_near_edge": float(bar["high"]),
            "fvg_width_pips": 5.0,
        },
    )
    result = wick_penetration_ratio(sig, df)
    assert result is not None
    assert 0 <= result <= 1


def test_impulse_body_ratio_returns_value() -> None:
    df = _make_candles(n=50)
    formation_time = df.index[25].isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata={"fvg_formation_time": formation_time},
    )
    result = impulse_body_ratio(sig, df)
    assert result is not None
    assert 0 <= result <= 1


# ---------------------------------------------------------------------------
# nova_candle.py candle-dependent params
# ---------------------------------------------------------------------------


def test_body_atr_ratio_nova() -> None:
    df = _make_candles(n=50)
    nova_meta = {"open": 1.08500, "high": 1.08700, "low": 1.08500, "close": 1.08680}
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), metadata=nova_meta,
    )
    result = body_atr_ratio(sig, df)
    assert result is not None
    assert result > 0


def test_risk_atr_ratio_nova() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), risk_pips=12.0,
    )
    result = risk_atr_ratio(sig, df)
    assert result is not None
    assert result > 0
