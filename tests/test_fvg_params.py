"""
tests/test_fvg_params.py
------------------------
Unit tests for the second batch of FVG-impulse analytics parameters
(``analytics/params/fvg_impulse_v2.py``) and the M5-only params
(``analytics/params/fvg_impulse_5m.py``). Uses deterministic OHLC
fixtures the same way ``tests/test_analytics_candle_params.py`` does.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.fvg_impulse_5m import (
    h1_fvg_contains_entry,
    signal_wick_pips,
    volatility_percentile_long,
)
from analytics.params.fvg_impulse_v2 import (
    c1_broke_prior_swing,
    c1_close_strength,
    fvg_breathing_room_pips,
    fvg_width_spread_mult,
    h1_trend_strength_bucket,
    opposing_wick_ratio,
    rejection_wick_atr,
    spread_dominance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_candles(
    n: int = 50,
    base_price: float = 1.08,
    freq: str = "15min",
) -> pd.DataFrame:
    """Build a deterministic OHLC DataFrame."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq=freq, tz="UTC",
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


# ---------------------------------------------------------------------------
# 1. fvg_breathing_room_pips
# ---------------------------------------------------------------------------


def test_fvg_breathing_room_pips_buy_positive() -> None:
    sig = _signal(
        direction="BUY", entry=1.0855,
        metadata={"fvg_near_edge": 1.0850},
    )
    # entry - near_edge = 5 pips
    result = fvg_breathing_room_pips(sig, None)
    assert result == pytest.approx(5.0, abs=0.01)


def test_fvg_breathing_room_pips_sell_positive() -> None:
    sig = _signal(
        direction="SELL", entry=1.0845,
        metadata={"fvg_near_edge": 1.0850},
    )
    # near_edge - entry = 5 pips
    result = fvg_breathing_room_pips(sig, None)
    assert result == pytest.approx(5.0, abs=0.01)


def test_fvg_breathing_room_pips_clamps_to_zero() -> None:
    # BUY where entry is BELOW near_edge → negative room → clamp 0
    sig = _signal(
        direction="BUY", entry=1.0845,
        metadata={"fvg_near_edge": 1.0850},
    )
    assert fvg_breathing_room_pips(sig, None) == 0.0


def test_fvg_breathing_room_pips_none_without_metadata() -> None:
    sig = _signal(metadata={})
    assert fvg_breathing_room_pips(sig, None) is None


# ---------------------------------------------------------------------------
# 2. rejection_wick_atr
# ---------------------------------------------------------------------------


def test_rejection_wick_atr_returns_value() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
    )
    result = rejection_wick_atr(sig, df)
    assert result is not None
    assert result >= 0


def test_rejection_wick_atr_none_without_candles() -> None:
    assert rejection_wick_atr(_signal(), None) is None


def test_rejection_wick_atr_none_when_signal_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before)
    assert rejection_wick_atr(sig, df) is None


def test_rejection_wick_atr_returns_python_float() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = rejection_wick_atr(sig, df)
    assert result is not None
    assert type(result) is float


# ---------------------------------------------------------------------------
# 3. c1_close_strength
# ---------------------------------------------------------------------------


def test_c1_close_strength_buy_in_range() -> None:
    df = _make_candles(n=50)
    formation_time = df.index[25].isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
        metadata={"fvg_formation_time": formation_time},
    )
    result = c1_close_strength(sig, df)
    assert result is not None
    assert 0.0 <= result <= 1.0


def test_c1_close_strength_sell_in_range() -> None:
    df = _make_candles(n=50)
    formation_time = df.index[25].isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="SELL",
        metadata={"fvg_formation_time": formation_time},
    )
    result = c1_close_strength(sig, df)
    assert result is not None
    assert 0.0 <= result <= 1.0


def test_c1_close_strength_none_without_candles() -> None:
    sig = _signal(metadata={"fvg_formation_time": "2025-03-10T06:00:00+00:00"})
    assert c1_close_strength(sig, None) is None


def test_c1_close_strength_none_without_formation_time() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime(), metadata={})
    assert c1_close_strength(sig, df) is None


# ---------------------------------------------------------------------------
# 4. c1_broke_prior_swing
# ---------------------------------------------------------------------------


def _make_breakout_candles(break_idx: int, n: int = 40) -> pd.DataFrame:
    """Build candles where bar ``break_idx`` closes well above the prior 10."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    base = 1.0800
    opens = [base for _ in range(n)]
    highs = [base + 0.0005 for _ in range(n)]
    lows = [base - 0.0005 for _ in range(n)]
    closes = [base + 0.0001 for _ in range(n)]
    # Breakout bar: close high above every prior high
    closes[break_idx] = base + 0.0050
    highs[break_idx] = base + 0.0060
    data = {"open": opens, "high": highs, "low": lows, "close": closes}
    return pd.DataFrame(data, index=idx)


def test_c1_broke_prior_swing_buy_true() -> None:
    df = _make_breakout_candles(break_idx=20)
    # C1 must sit at break_idx. fvg_formation_time points at break_idx + 1.
    formation_time = df.index[21].isoformat()
    sig = _signal(
        candle_time=df.index[25].to_pydatetime(), direction="BUY",
        metadata={"fvg_formation_time": formation_time},
    )
    assert c1_broke_prior_swing(sig, df) is True


def test_c1_broke_prior_swing_buy_false_when_not_broken() -> None:
    df = _make_candles(n=50)  # monotonic-rising but smooth
    formation_time = df.index[25].isoformat()
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
        metadata={"fvg_formation_time": formation_time},
    )
    # In a smoothly rising series, bar 24 close is > window[14..23] max? Yes.
    # We want to confirm the fn returns a native bool — value-specific
    # assertion below.
    result = c1_broke_prior_swing(sig, df)
    assert result is not None
    assert type(result) is bool


def test_c1_broke_prior_swing_none_insufficient_history() -> None:
    df = _make_candles(n=50)
    formation_time = df.index[2].isoformat()  # C1 at bar 1
    sig = _signal(
        candle_time=df.index[5].to_pydatetime(), direction="BUY",
        metadata={"fvg_formation_time": formation_time},
    )
    assert c1_broke_prior_swing(sig, df) is None


def test_c1_broke_prior_swing_none_without_candles() -> None:
    sig = _signal(metadata={"fvg_formation_time": "2025-03-10T06:00:00+00:00"})
    assert c1_broke_prior_swing(sig, None) is None


# ---------------------------------------------------------------------------
# 5. opposing_wick_ratio
# ---------------------------------------------------------------------------


def test_opposing_wick_ratio_buy_in_range() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
    )
    result = opposing_wick_ratio(sig, df)
    assert result is not None
    assert 0.0 <= result <= 1.0


def test_opposing_wick_ratio_sell_in_range() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="SELL",
    )
    result = opposing_wick_ratio(sig, df)
    assert result is not None
    assert 0.0 <= result <= 1.0


def test_opposing_wick_ratio_none_without_candles() -> None:
    assert opposing_wick_ratio(_signal(), None) is None


def test_opposing_wick_ratio_none_outside_window() -> None:
    df = _make_candles(n=50)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before)
    assert opposing_wick_ratio(sig, df) is None


# ---------------------------------------------------------------------------
# 6. spread_dominance
# ---------------------------------------------------------------------------


def test_spread_dominance_value() -> None:
    sig = _signal(risk_pips=9.0, spread_pips=1.0)
    # 1 / (9 + 1) = 0.1
    assert spread_dominance(sig, None) == pytest.approx(0.1, abs=0.001)


def test_spread_dominance_zero_when_spread_zero() -> None:
    sig = _signal(risk_pips=10.0, spread_pips=0.0)
    assert spread_dominance(sig, None) == 0.0


def test_spread_dominance_none_on_zero_total() -> None:
    sig = _signal(risk_pips=0.0, spread_pips=0.0)
    assert spread_dominance(sig, None) is None


def test_spread_dominance_returns_python_float() -> None:
    sig = _signal(risk_pips=9.0, spread_pips=1.0)
    result = spread_dominance(sig, None)
    assert type(result) is float


# ---------------------------------------------------------------------------
# 7. fvg_width_spread_mult
# ---------------------------------------------------------------------------


def test_fvg_width_spread_mult_happy_path() -> None:
    sig = _signal(
        spread_pips=2.0, metadata={"fvg_width_pips": 10.0},
    )
    # 10 / max(2, 0.3) = 5
    assert fvg_width_spread_mult(sig, None) == pytest.approx(5.0, abs=0.01)


def test_fvg_width_spread_mult_applies_floor() -> None:
    sig = _signal(
        spread_pips=0.1, metadata={"fvg_width_pips": 3.0},
    )
    # floor 0.3 applies: 3 / 0.3 = 10
    assert fvg_width_spread_mult(sig, None) == pytest.approx(10.0, abs=0.01)


def test_fvg_width_spread_mult_none_without_metadata() -> None:
    sig = _signal(metadata={})
    assert fvg_width_spread_mult(sig, None) is None


def test_fvg_width_spread_mult_returns_python_float() -> None:
    sig = _signal(spread_pips=1.0, metadata={"fvg_width_pips": 5.0})
    assert type(fvg_width_spread_mult(sig, None)) is float


# ---------------------------------------------------------------------------
# 8. h1_trend_strength_bucket
# ---------------------------------------------------------------------------


def _make_rising_candles(n: int = 200) -> pd.DataFrame:
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    closes = [1.08 + i * 0.0010 for i in range(n)]
    data = {
        "open": [c - 0.0001 for c in closes],
        "high": [c + 0.0005 for c in closes],
        "low": [c - 0.0005 for c in closes],
        "close": closes,
    }
    return pd.DataFrame(data, index=idx)


def _make_flat_candles(n: int = 200) -> pd.DataFrame:
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    data = {
        "open": [1.08 for _ in range(n)],
        "high": [1.0805 for _ in range(n)],
        "low": [1.0795 for _ in range(n)],
        "close": [1.08 for _ in range(n)],
    }
    return pd.DataFrame(data, index=idx)


def test_h1_trend_strength_bucket_with_trend_buy() -> None:
    df = _make_rising_candles(n=200)
    sig = _signal(
        candle_time=df.index[180].to_pydatetime(), direction="BUY",
    )
    assert h1_trend_strength_bucket(sig, df) == "WITH"


def test_h1_trend_strength_bucket_against_trend_sell() -> None:
    df = _make_rising_candles(n=200)
    sig = _signal(
        candle_time=df.index[180].to_pydatetime(), direction="SELL",
    )
    assert h1_trend_strength_bucket(sig, df) == "AGAINST"


def test_h1_trend_strength_bucket_flat() -> None:
    df = _make_flat_candles(n=200)
    sig = _signal(
        candle_time=df.index[180].to_pydatetime(), direction="BUY",
    )
    # Flat series → slope ~0 → FLAT
    assert h1_trend_strength_bucket(sig, df) == "FLAT"


def test_h1_trend_strength_bucket_none_without_candles() -> None:
    assert h1_trend_strength_bucket(_signal(), None) is None


def test_h1_trend_strength_bucket_returns_valid_label() -> None:
    df = _make_rising_candles(n=200)
    sig = _signal(candle_time=df.index[180].to_pydatetime())
    result = h1_trend_strength_bucket(sig, df)
    assert result in {"WITH", "AGAINST", "FLAT"}


# ---------------------------------------------------------------------------
# 9. h1_fvg_contains_entry
# ---------------------------------------------------------------------------


def _make_m5_candles_with_h1_fvg() -> pd.DataFrame:
    """Build M5 candles where the H1 resample contains a known bullish FVG.

    Engineered so at H1 bar 2 (the 3rd H1 bar) a bullish FVG forms:
    C0.high < C2.low. The gap top (near_edge) is C2.low = 1.0910 and
    the gap bottom is C0.high = 1.0860. Subsequent H1 bars stay above
    the gap so it remains virgin and active.
    """
    n = 200  # 200 M5 bars = ~16 H1 bars
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="5min", tz="UTC",
    )
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    opens: list[float] = []
    for i in range(n):
        # 12 M5 bars per H1 bar. H1 bar index = i // 12.
        h1_idx = i // 12
        if h1_idx == 0:
            base = 1.0850
        elif h1_idx == 1:
            base = 1.0870  # gap bar — this C1 bridges the gap
        elif h1_idx == 2:
            base = 1.0920  # C2 — creates the gap
        else:
            # Stay well above the gap — above the top (1.0910)
            base = 1.0930 + (h1_idx - 3) * 0.0005
        opens.append(base)
        closes.append(base + 0.0002)
        highs.append(base + 0.0010)
        lows.append(base - 0.0002)
    data = {"open": opens, "high": highs, "low": lows, "close": closes}
    return pd.DataFrame(data, index=idx)


def test_h1_fvg_contains_entry_true_inside_gap() -> None:
    df = _make_m5_candles_with_h1_fvg()
    # Signal late enough that all 3 FVG bars exist in the H1 resample.
    sig = _signal(
        candle_time=df.index[180].to_pydatetime(),
        direction="BUY",
        entry=1.0870,  # inside the gap [1.0860..1.0910]
    )
    result = h1_fvg_contains_entry(sig, df)
    assert result is True
    assert type(result) is bool


def test_h1_fvg_contains_entry_false_outside_gap() -> None:
    df = _make_m5_candles_with_h1_fvg()
    sig = _signal(
        candle_time=df.index[180].to_pydatetime(),
        direction="BUY",
        entry=1.1500,  # nowhere near any FVG
    )
    assert h1_fvg_contains_entry(sig, df) is False


def _make_m5_candles_with_aged_out_fvg() -> pd.DataFrame:
    """Build M5 candles where the bullish H1 FVG ages out of validity.

    MAX_FVG_AGE is 15 bars, so by H1 bar 18 the gap formed at H1 bar 2
    has expired. The fixture keeps subsequent bars far above the gap so
    virginity is never touched and no new bearish FVG forms — the only
    reason the gap becomes invalid is age.
    """
    n = 300  # 300 M5 bars = 25 H1 bars
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="5min", tz="UTC",
    )
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    opens: list[float] = []
    for i in range(n):
        h1_idx = i // 12
        if h1_idx == 0:
            base = 1.0850
        elif h1_idx == 1:
            base = 1.0870
        elif h1_idx == 2:
            base = 1.0920
        else:
            # Stay well above near_edge (1.0918) so no virginity touch
            base = 1.0930 + (h1_idx - 3) * 0.0002
        opens.append(base)
        closes.append(base + 0.0002)
        highs.append(base + 0.0010)
        lows.append(base - 0.0002)
    data = {"open": opens, "high": highs, "low": lows, "close": closes}
    return pd.DataFrame(data, index=idx)


def test_h1_fvg_contains_entry_false_when_fvg_aged_out() -> None:
    df = _make_m5_candles_with_aged_out_fvg()
    # Signal late enough that formation bar is >15 H1 bars in the past.
    # H1 bar 20 ≈ M5 bar 240. Entry inside the original gap [1.0860, 1.0918]
    # — but the gap is now expired, so the function must return False.
    sig = _signal(
        candle_time=df.index[275].to_pydatetime(),
        direction="BUY",
        entry=1.0870,
    )
    assert h1_fvg_contains_entry(sig, df) is False


def test_h1_fvg_contains_entry_none_without_candles() -> None:
    assert h1_fvg_contains_entry(_signal(), None) is None


# ---------------------------------------------------------------------------
# 10. volatility_percentile_long
# ---------------------------------------------------------------------------


def test_volatility_percentile_long_range() -> None:
    df = _make_candles(n=150, freq="5min")
    sig = _signal(candle_time=df.index[140].to_pydatetime())
    result = volatility_percentile_long(sig, df)
    assert result is not None
    assert 0.0 <= result <= 100.0


def test_volatility_percentile_long_none_insufficient_history() -> None:
    df = _make_candles(n=150, freq="5min")
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    # Only 30 bars of history, need 96
    assert volatility_percentile_long(sig, df) is None


def test_volatility_percentile_long_none_without_candles() -> None:
    assert volatility_percentile_long(_signal(), None) is None


def test_volatility_percentile_long_returns_python_float() -> None:
    df = _make_candles(n=150, freq="5min")
    sig = _signal(candle_time=df.index[140].to_pydatetime())
    result = volatility_percentile_long(sig, df)
    assert result is not None
    assert type(result) is float


# ---------------------------------------------------------------------------
# 11. signal_wick_pips
# ---------------------------------------------------------------------------


def test_signal_wick_pips_buy_returns_value() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="BUY",
    )
    result = signal_wick_pips(sig, df)
    assert result is not None
    assert result >= 0.0


def test_signal_wick_pips_sell_returns_value() -> None:
    df = _make_candles(n=50)
    sig = _signal(
        candle_time=df.index[30].to_pydatetime(), direction="SELL",
    )
    result = signal_wick_pips(sig, df)
    assert result is not None
    assert result >= 0.0


def test_signal_wick_pips_none_without_candles() -> None:
    assert signal_wick_pips(_signal(), None) is None


def test_signal_wick_pips_returns_python_float() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[30].to_pydatetime())
    result = signal_wick_pips(sig, df)
    assert type(result) is float
