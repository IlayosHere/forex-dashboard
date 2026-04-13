"""
tests/test_nova_params.py
-------------------------
Unit tests for Nova-candle analytics parameters defined in
:mod:`analytics.params.nova_candle_v2`. Tests use deterministic OHLC
fixtures and the same ``_signal`` / ``_make_candles`` patterns as
:mod:`tests.test_analytics_candle_params`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.nova_candle_v2 import (
    bos_swing_leg_atr,
    gap_pips,
    open_wick_pips,
    open_wick_zero,
    prior_body_atr_ratio,
    prior_candle_direction,
    range_atr_ratio,
    sl_swing_distance_bars,
)


def _make_candles(n: int = 50, base_price: float = 1.08) -> pd.DataFrame:
    """Build a deterministic M15 OHLC DataFrame (UTC, 15m freq)."""
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
    entry: float = 1.0850,
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
    sig.entry = entry
    sig.risk_pips = risk_pips
    sig.spread_pips = spread_pips
    sig.signal_metadata = metadata or {}
    return sig


def _nova_meta(
    open_: float = 1.08500,
    high: float = 1.08700,
    low: float = 1.08480,
    close: float = 1.08680,
    **extras: Any,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "open": open_, "high": high, "low": low, "close": close,
    }
    meta.update(extras)
    return meta


# ---------------------------------------------------------------------------
# sl_swing_distance_bars
# ---------------------------------------------------------------------------


def test_sl_swing_distance_bars_happy_path() -> None:
    """BOS bar 5 M15 bars before the signal should return exactly 5."""
    df = _make_candles(n=60)
    signal_idx = 30
    bos_idx = 25
    bos_iso = df.index[bos_idx].to_pydatetime().isoformat()
    sig = _signal(
        candle_time=df.index[signal_idx].to_pydatetime(),
        metadata=_nova_meta(bos_candle_time=bos_iso, bos_swing_price=1.08400),
    )
    result = sl_swing_distance_bars(sig, df)
    assert result == 5
    assert type(result) is int


def test_sl_swing_distance_bars_none_without_candles() -> None:
    bos_iso = datetime(2025, 3, 10, 5, 0, tzinfo=timezone.utc).isoformat()
    sig = _signal(metadata=_nova_meta(bos_candle_time=bos_iso))
    assert sl_swing_distance_bars(sig, None) is None


def test_sl_swing_distance_bars_none_when_bos_used_false() -> None:
    """Fallback SL path — bos_candle_time is None → return None."""
    df = _make_candles(n=60)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata=_nova_meta(bos_candle_time=None, bos_swing_price=None),
    )
    assert sl_swing_distance_bars(sig, df) is None


def test_sl_swing_distance_bars_none_when_bos_outside_window() -> None:
    df = _make_candles(n=60)
    far_past = (df.index[0].to_pydatetime() - pd.Timedelta(days=10)).isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata=_nova_meta(bos_candle_time=far_past),
    )
    assert sl_swing_distance_bars(sig, df) is None


# ---------------------------------------------------------------------------
# bos_swing_leg_atr
# ---------------------------------------------------------------------------


def test_bos_swing_leg_atr_happy_path() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        entry=1.08500,
        metadata=_nova_meta(bos_swing_price=1.08400),
    )
    result = bos_swing_leg_atr(sig, df)
    assert result is not None
    assert result > 0
    assert isinstance(result, float)


def test_bos_swing_leg_atr_none_without_candles() -> None:
    sig = _signal(metadata=_nova_meta(bos_swing_price=1.08400))
    assert bos_swing_leg_atr(sig, None) is None


def test_bos_swing_leg_atr_none_when_bos_price_missing() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata=_nova_meta(bos_swing_price=None),
    )
    assert bos_swing_leg_atr(sig, df) is None


def test_bos_swing_leg_atr_none_when_signal_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(
        candle_time=before,
        entry=1.08500,
        metadata=_nova_meta(bos_swing_price=1.08400),
    )
    assert bos_swing_leg_atr(sig, df) is None


# ---------------------------------------------------------------------------
# open_wick_pips
# ---------------------------------------------------------------------------


def test_open_wick_pips_buy() -> None:
    # BUY: open=1.0850, low=1.0848 → 2.0 pips
    sig = _signal(
        direction="BUY",
        metadata=_nova_meta(open_=1.0850, high=1.0870, low=1.0848, close=1.0868),
    )
    result = open_wick_pips(sig, None)
    assert result == pytest.approx(2.0, abs=0.001)
    assert isinstance(result, float)


def test_open_wick_pips_sell() -> None:
    # SELL: open=1.0850, high=1.0853 → 3.0 pips
    sig = _signal(
        direction="SELL",
        metadata=_nova_meta(open_=1.0850, high=1.0853, low=1.0830, close=1.0832),
    )
    result = open_wick_pips(sig, None)
    assert result == pytest.approx(3.0, abs=0.001)


def test_open_wick_pips_none_without_metadata() -> None:
    sig = _signal(metadata={})
    assert open_wick_pips(sig, None) is None


def test_open_wick_pips_zero_when_open_equals_low_buy() -> None:
    sig = _signal(
        direction="BUY",
        metadata=_nova_meta(open_=1.0850, high=1.0870, low=1.0850, close=1.0868),
    )
    assert open_wick_pips(sig, None) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# open_wick_zero
# ---------------------------------------------------------------------------


def test_open_wick_zero_true_buy() -> None:
    sig = _signal(
        direction="BUY",
        metadata=_nova_meta(open_=1.0850, high=1.0870, low=1.0850, close=1.0868),
    )
    result = open_wick_zero(sig, None)
    assert result is True
    assert type(result) is bool  # catch numpy.bool_ leaks


def test_open_wick_zero_false_buy_small_wick() -> None:
    # open=1.08500, low=1.08495 → 0.5 pip wick, not zero
    sig = _signal(
        direction="BUY",
        metadata=_nova_meta(open_=1.08500, high=1.08700, low=1.08495, close=1.08680),
    )
    result = open_wick_zero(sig, None)
    assert result is False
    assert type(result) is bool


def test_open_wick_zero_true_sell() -> None:
    sig = _signal(
        direction="SELL",
        metadata=_nova_meta(open_=1.0850, high=1.0850, low=1.0830, close=1.0832),
    )
    result = open_wick_zero(sig, None)
    assert result is True
    assert type(result) is bool


def test_open_wick_zero_none_without_metadata() -> None:
    sig = _signal(metadata={})
    assert open_wick_zero(sig, None) is None


# ---------------------------------------------------------------------------
# range_atr_ratio
# ---------------------------------------------------------------------------


def test_range_atr_ratio_happy_path() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(),
        metadata=_nova_meta(open_=1.08500, high=1.08700, low=1.08400, close=1.08680),
    )
    result = range_atr_ratio(sig, df)
    assert result is not None
    assert result > 0
    assert isinstance(result, float)


def test_range_atr_ratio_none_without_candles() -> None:
    sig = _signal(metadata=_nova_meta())
    assert range_atr_ratio(sig, None) is None


def test_range_atr_ratio_none_without_metadata() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime(), metadata={})
    assert range_atr_ratio(sig, df) is None


def test_range_atr_ratio_none_when_signal_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before, metadata=_nova_meta())
    assert range_atr_ratio(sig, df) is None


# ---------------------------------------------------------------------------
# prior_candle_direction
# ---------------------------------------------------------------------------


def _make_candles_with_prior(
    prior_open: float, prior_close: float, signal_idx: int = 30,
) -> tuple[pd.DataFrame, datetime]:
    """Build a DataFrame where the bar at signal_idx-1 has a specific body."""
    df = _make_candles(n=60)
    # Overwrite the prior bar
    df.iloc[signal_idx - 1, df.columns.get_loc("open")] = prior_open
    df.iloc[signal_idx - 1, df.columns.get_loc("close")] = prior_close
    df.iloc[signal_idx - 1, df.columns.get_loc("high")] = max(
        prior_open, prior_close,
    ) + 0.0001
    df.iloc[signal_idx - 1, df.columns.get_loc("low")] = min(
        prior_open, prior_close,
    ) - 0.0001
    return df, df.index[signal_idx].to_pydatetime()


def test_prior_candle_direction_same() -> None:
    # Prior green (BUY-colored), signal BUY → SAME
    df, ct = _make_candles_with_prior(prior_open=1.08500, prior_close=1.08520)
    sig = _signal(candle_time=ct, direction="BUY")
    result = prior_candle_direction(sig, df)
    assert result == "SAME"


def test_prior_candle_direction_opposite() -> None:
    # Prior red (SELL-colored), signal BUY → OPPOSITE
    df, ct = _make_candles_with_prior(prior_open=1.08520, prior_close=1.08500)
    sig = _signal(candle_time=ct, direction="BUY")
    result = prior_candle_direction(sig, df)
    assert result == "OPPOSITE"


def test_prior_candle_direction_doji() -> None:
    # Prior body <0.5 pip → DOJI
    df, ct = _make_candles_with_prior(prior_open=1.08500, prior_close=1.08502)
    sig = _signal(candle_time=ct, direction="BUY")
    result = prior_candle_direction(sig, df)
    assert result == "DOJI"


def test_prior_candle_direction_none_without_candles() -> None:
    assert prior_candle_direction(_signal(), None) is None


def test_prior_candle_direction_none_when_no_prior_bar() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[0].to_pydatetime(), direction="BUY")
    assert prior_candle_direction(sig, df) is None


# ---------------------------------------------------------------------------
# prior_body_atr_ratio
# ---------------------------------------------------------------------------


def test_prior_body_atr_ratio_happy_path() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = prior_body_atr_ratio(sig, df)
    assert result is not None
    assert result > 0
    assert isinstance(result, float)


def test_prior_body_atr_ratio_none_without_candles() -> None:
    assert prior_body_atr_ratio(_signal(), None) is None


def test_prior_body_atr_ratio_none_when_no_prior_bar() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[0].to_pydatetime())
    assert prior_body_atr_ratio(sig, df) is None


def test_prior_body_atr_ratio_none_when_signal_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before)
    assert prior_body_atr_ratio(sig, df) is None


# ---------------------------------------------------------------------------
# gap_pips
# ---------------------------------------------------------------------------


def test_gap_pips_happy_path() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = gap_pips(sig, df)
    assert result is not None
    assert result >= 0
    assert isinstance(result, float)


def test_gap_pips_zero_when_continuous() -> None:
    # Build DF where signal open exactly equals prior close
    df = _make_candles(n=50)
    df.iloc[29, df.columns.get_loc("close")] = 1.08600
    df.iloc[30, df.columns.get_loc("open")] = 1.08600
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = gap_pips(sig, df)
    assert result == pytest.approx(0.0, abs=1e-9)


def test_gap_pips_nonzero_with_explicit_gap() -> None:
    df = _make_candles(n=50)
    df.iloc[29, df.columns.get_loc("close")] = 1.08600
    df.iloc[30, df.columns.get_loc("open")] = 1.08620  # 2-pip gap
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = gap_pips(sig, df)
    assert result == pytest.approx(2.0, abs=0.001)


def test_gap_pips_none_without_candles() -> None:
    assert gap_pips(_signal(), None) is None


def test_gap_pips_none_when_no_prior_bar() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[0].to_pydatetime())
    assert gap_pips(sig, df) is None
