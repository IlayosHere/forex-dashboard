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
    impulse_size_atr,
    rejection_body_ratio,
    wick_penetration_ratio,
)
from analytics.params.nova_candle import body_atr_ratio


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
    # Data is monotonically rising and the signal sits at M15 bar 110 (H1
    # bar 27), where the EMA-20 at that bar is above the EMA-20 three H1
    # bars earlier, so BUY should be aligned.
    assert result is True


def test_trend_h1_aligned_none_without_candles() -> None:
    assert trend_h1_aligned(_signal(), None) is None


def test_volatility_percentile_range() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[40].to_pydatetime())
    result = volatility_percentile(sig, df)
    assert result is not None
    assert 0 <= result <= 100
    # Monotonically rising synthetic data produces a stable ATR once the
    # 14-bar warmup passes, so every bar in the 20-bar window should tie
    # with the signal bar → percentile = 100.
    assert result == pytest.approx(100.0, abs=0.01)


def test_risk_pips_atr_returns_ratio() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime(), risk_pips=15.0)
    result = risk_pips_atr(sig, df)
    assert result is not None
    assert result > 0


# ---------------------------------------------------------------------------
# Signal-bar correctness — trend_h1_aligned
# ---------------------------------------------------------------------------


def _make_rise_fall_candles(n: int = 140) -> pd.DataFrame:
    """Build an M15 OHLC DataFrame that rises sharply then falls sharply.

    Close prices rise from bar 0 to bar n//2 then fall back down. The
    resulting H1 EMA-20 trend is rising in the first half of the window
    and falling in the second half, which lets tests distinguish between
    computing the trend at the signal's own bar versus at the window tail.
    """
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    half = n // 2
    closes: list[float] = []
    for i in range(n):
        if i <= half:
            closes.append(1.08 + i * 0.0010)
        else:
            closes.append(1.08 + (2 * half - i) * 0.0010)
    data = {
        "open": [c - 0.0001 for c in closes],
        "high": [c + 0.0005 for c in closes],
        "low": [c - 0.0005 for c in closes],
        "close": closes,
    }
    return pd.DataFrame(data, index=idx)


def test_trend_h1_aligned_uses_signal_bar_not_window_tail() -> None:
    """BUY in the rising half should align; BUY in the falling half must not.

    If the function computed the trend at the last bar of the fetched window
    (the old buggy behavior), both signals would return the same value.
    """
    df = _make_rise_fall_candles(n=140)
    # Rising-half signal — roughly 1/3 of the way through the window
    rising_sig = _signal(
        candle_time=df.index[45].to_pydatetime(), direction="BUY",
    )
    # Falling-half signal — near the end of the window, well past the peak
    falling_sig = _signal(
        candle_time=df.index[125].to_pydatetime(), direction="BUY",
    )
    rising_result = trend_h1_aligned(rising_sig, df)
    falling_result = trend_h1_aligned(falling_sig, df)
    assert rising_result is True
    assert falling_result is False


def test_trend_h1_aligned_returns_none_when_signal_outside_window() -> None:
    df = _make_candles(n=120, base_price=1.08)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before, direction="BUY")
    assert trend_h1_aligned(sig, df) is None


def test_trend_h1_aligned_returns_none_when_signal_too_early_for_lookback() -> None:
    """Signal at the first H1 bar lacks the 3-bar EMA lookback."""
    df = _make_candles(n=120, base_price=1.08)
    # df.index[0] is at 00:00 UTC, which is the first H1 bar → idx == 0 < 3
    sig = _signal(candle_time=df.index[0].to_pydatetime(), direction="BUY")
    assert trend_h1_aligned(sig, df) is None


# ---------------------------------------------------------------------------
# Signal-bar correctness — volatility_percentile
# ---------------------------------------------------------------------------


def _make_spike_candles(n: int, spike_idx: int) -> pd.DataFrame:
    """Build an M15 OHLC DataFrame with a single ATR spike at spike_idx.

    All bars have a ~10-pip range except the spike bar which has a ~100-pip
    range, creating a single tall ATR value at that index.
    """
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    base = 1.08
    opens = [base for _ in range(n)]
    closes = [base + 0.0001 for _ in range(n)]
    highs = [base + 0.0005 for _ in range(n)]
    lows = [base - 0.0005 for _ in range(n)]
    # Inject a wide-range spike bar
    highs[spike_idx] = base + 0.0100
    lows[spike_idx] = base - 0.0100
    data = {"open": opens, "high": highs, "low": lows, "close": closes}
    return pd.DataFrame(data, index=idx)


def test_volatility_percentile_uses_signal_bar_not_window_tail() -> None:
    """A signal at an ATR spike must score high; a signal at a calm bar low.

    If the function computed the percentile at the last bar of the fetched
    window (the old buggy behavior), both signals would return the same
    value regardless of where they were placed.
    """
    spike_idx = 40
    df = _make_spike_candles(n=80, spike_idx=spike_idx)
    # Signal exactly at the spike
    spike_sig = _signal(candle_time=df.index[spike_idx].to_pydatetime())
    spike_result = volatility_percentile(spike_sig, df)
    assert spike_result is not None
    assert spike_result >= 90.0
    # Signal at a calm bar where the spike's elevated ATR-14 values
    # (bars spike_idx..spike_idx+13, since ATR-14 is a 14-bar rolling
    # mean that retains the spike TR) still sit inside the 20-bar window
    # ending at the signal bar. The current ATR is back at baseline, so
    # the percentile should land well below 50.
    calm_sig = _signal(candle_time=df.index[60].to_pydatetime())
    calm_result = volatility_percentile(calm_sig, df)
    assert calm_result is not None
    assert calm_result <= 50.0


def test_volatility_percentile_returns_none_when_signal_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before)
    assert volatility_percentile(sig, df) is None


def test_volatility_percentile_returns_none_when_insufficient_lookback() -> None:
    """Bar 10 lacks 20 valid ATR values (ATR-14 is NaN for the first 13 bars)."""
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[10].to_pydatetime())
    assert volatility_percentile(sig, df) is None


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
# fvg_impulse.py — impulse_size_atr
# ---------------------------------------------------------------------------


def test_impulse_size_atr_returns_positive_float() -> None:
    """Happy path: C1 range / ATR returns a positive float."""
    df = _make_candles(n=50)
    formation_time = df.index[25].isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata={"fvg_formation_time": formation_time},
    )
    result = impulse_size_atr(sig, df)
    assert result is not None
    assert result > 0
    assert type(result) is float


def test_impulse_size_atr_none_without_candles() -> None:
    """Returns None when candles arg is None."""
    sig = _signal(metadata={"fvg_formation_time": "2025-03-10T06:15:00+00:00"})
    assert impulse_size_atr(sig, None) is None


def test_impulse_size_atr_none_without_formation_time() -> None:
    """Returns None when fvg_formation_time is absent from metadata."""
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata={},  # no fvg_formation_time
    )
    assert impulse_size_atr(sig, df) is None


def test_impulse_size_atr_none_when_atr_zero() -> None:
    """Returns None when all candles have identical prices (ATR = 0)."""
    n = 50
    idx = pd.date_range("2025-03-10 00:00", periods=n, freq="15min", tz="UTC")
    # Flat candles: open == high == low == close → ATR is 0
    flat_df = pd.DataFrame(
        {"open": [1.08] * n, "high": [1.08] * n, "low": [1.08] * n, "close": [1.08] * n},
        index=idx,
    )
    formation_time = flat_df.index[25].isoformat()
    sig = _signal(
        candle_time=flat_df.index[30].to_pydatetime(),
        metadata={"fvg_formation_time": formation_time},
    )
    assert impulse_size_atr(sig, flat_df) is None


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
