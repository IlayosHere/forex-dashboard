"""
tests/test_structure_params.py
------------------------------
Unit tests for the cross-strategy structure / macro / regime parameters
(``analytics/params/structure.py``, ``macro.py``, ``regime.py``) plus the
updated ``spread_tier`` (``analytics/params/nova_candle.py``).

Uses deterministic DataFrame fixtures matching the style of
``tests/test_analytics_candle_params.py``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from analytics.params.macro import (
    d1_trend,
    dist_to_prior_day_hl_atr,
    htf_range_position_d1,
)
from analytics.params.nova_candle import spread_tier
from analytics.params.regime import (
    range_bound_efficiency,
    range_compression_ratio,
    spread_atr_ratio,
    trail_extension_atr,
)
from analytics.params.structure import (
    bars_since_h1_extreme,
    dist_to_round_atr,
    h1_swing_position,
    hour_bucket,
    minutes_into_session,
)
from analytics.registry import get_params_for_strategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_candles(
    n: int = 200, base_price: float = 1.08, freq: str = "15min",
) -> pd.DataFrame:
    """Build a deterministic OHLC DataFrame with monotonic drift."""
    idx = pd.date_range("2025-07-01 00:00", periods=n, freq=freq, tz="UTC")
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
    entry: float = 1.08500,
    risk_pips: float = 10.0,
    spread_pips: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> MagicMock:
    sig = MagicMock()
    sig.candle_time = candle_time or datetime(
        2025, 7, 1, 10, 0, tzinfo=timezone.utc,
    )
    sig.symbol = symbol
    sig.direction = direction
    sig.entry = entry
    sig.risk_pips = risk_pips
    sig.spread_pips = spread_pips
    sig.signal_metadata = metadata or {}
    return sig


# ---------------------------------------------------------------------------
# minutes_into_session
# ---------------------------------------------------------------------------

def test_minutes_into_session_london() -> None:
    """London session starts at 07:00 UTC; 08:30 → 90 minutes in."""
    sig = _signal(candle_time=datetime(2025, 7, 1, 8, 30, tzinfo=timezone.utc))
    result = minutes_into_session(sig, None)
    assert result == 90
    assert isinstance(result, int)


def test_minutes_into_session_asian_zero() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 0, 0, tzinfo=timezone.utc))
    assert minutes_into_session(sig, None) == 0


def test_minutes_into_session_close_returns_zero() -> None:
    """CLOSE session (21..23 UTC) returns 0, not minutes past 21:00."""
    sig = _signal(candle_time=datetime(2025, 7, 1, 22, 30, tzinfo=timezone.utc))
    assert minutes_into_session(sig, None) == 0


def test_minutes_into_session_dtype_int() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 10, 15, tzinfo=timezone.utc))
    result = minutes_into_session(sig, None)
    assert result is not None
    assert type(result) is int


# ---------------------------------------------------------------------------
# hour_bucket
# ---------------------------------------------------------------------------

def test_hour_bucket_asian() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 3, 0, tzinfo=timezone.utc))
    assert hour_bucket(sig, None) == "ASIAN_QUIET"


def test_hour_bucket_london_open() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 7, 30, tzinfo=timezone.utc))
    assert hour_bucket(sig, None) == "LONDON_OPEN"


def test_hour_bucket_london_ny() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 13, 0, tzinfo=timezone.utc))
    assert hour_bucket(sig, None) == "LONDON_NY"


def test_hour_bucket_ny_late_close() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 22, 0, tzinfo=timezone.utc))
    result = hour_bucket(sig, None)
    assert result == "NY_LATE_CLOSE"
    assert type(result) is str


# ---------------------------------------------------------------------------
# dist_to_round_atr
# ---------------------------------------------------------------------------

def test_dist_to_round_atr_returns_positive() -> None:
    df = _make_candles(n=100)
    sig = _signal(
        candle_time=df.index[50].to_pydatetime(),
        entry=1.08230,  # 23 pips from 1.08000, 27 pips from 1.08500
    )
    result = dist_to_round_atr(sig, df)
    assert result is not None
    assert result >= 0
    assert type(result) is float


def test_dist_to_round_atr_none_without_candles() -> None:
    sig = _signal(entry=1.08230)
    assert dist_to_round_atr(sig, None) is None


def test_dist_to_round_atr_jpy_pair() -> None:
    """JPY pairs: 50-pip round level step is 0.5 in price units."""
    df = _make_candles(n=100, base_price=150.00)
    # JPY candles need JPY pip scale; rebuild with 0.01 drift
    idx = pd.date_range("2025-07-01 00:00", periods=100, freq="15min", tz="UTC")
    data = {
        "open": [150.00 + i * 0.01 for i in range(100)],
        "high": [150.00 + i * 0.01 + 0.10 for i in range(100)],
        "low": [150.00 + i * 0.01 - 0.05 for i in range(100)],
        "close": [150.00 + i * 0.01 + 0.03 for i in range(100)],
    }
    jpy_df = pd.DataFrame(data, index=idx)
    sig = _signal(
        candle_time=jpy_df.index[50].to_pydatetime(),
        symbol="USDJPY",
        entry=150.23,  # 23 pips from 150.00, 27 pips from 150.50
    )
    result = dist_to_round_atr(sig, jpy_df)
    assert result is not None
    assert result >= 0


def test_dist_to_round_atr_none_on_zero_atr() -> None:
    """Signal outside the candle window → no ATR → None."""
    df = _make_candles(n=100)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before, entry=1.08230)
    assert dist_to_round_atr(sig, df) is None


# ---------------------------------------------------------------------------
# h1_swing_position
# ---------------------------------------------------------------------------

def test_h1_swing_position_near_high() -> None:
    """Monotonically rising data puts the signal near the window high."""
    df = _make_candles(n=300)
    sig = _signal(
        candle_time=df.index[250].to_pydatetime(),
        entry=1.10500,  # well above the rising baseline
    )
    result = h1_swing_position(sig, df)
    assert result == "near_high"


def test_h1_swing_position_none_without_candles() -> None:
    assert h1_swing_position(_signal(), None) is None


def test_h1_swing_position_insufficient_history() -> None:
    df = _make_candles(n=20)
    sig = _signal(candle_time=df.index[5].to_pydatetime(), entry=1.08050)
    assert h1_swing_position(sig, df) is None


def test_h1_swing_position_returns_str() -> None:
    df = _make_candles(n=300)
    sig = _signal(
        candle_time=df.index[200].to_pydatetime(), entry=1.09500,
    )
    result = h1_swing_position(sig, df)
    assert result is not None
    assert type(result) is str
    assert result in {"near_high", "near_low", "mid"}


# ---------------------------------------------------------------------------
# bars_since_h1_extreme
# ---------------------------------------------------------------------------

def test_bars_since_h1_extreme_returns_int() -> None:
    """Monotonically rising BUY signal: the window's low is at the oldest bar."""
    df = _make_candles(n=500)  # enough for 48+ H1 bars at the signal
    sig = _signal(
        candle_time=df.index[400].to_pydatetime(), direction="BUY",
    )
    result = bars_since_h1_extreme(sig, df)
    assert result is not None
    assert isinstance(result, int)
    assert result >= 0


def test_bars_since_h1_extreme_none_without_candles() -> None:
    assert bars_since_h1_extreme(_signal(), None) is None


def test_bars_since_h1_extreme_insufficient_history() -> None:
    df = _make_candles(n=80)  # only ~20 H1 bars, < 48 required
    sig = _signal(candle_time=df.index[70].to_pydatetime())
    assert bars_since_h1_extreme(sig, df) is None


def test_bars_since_h1_extreme_sell_path() -> None:
    """SELL uses max-high — on rising data it's at the most recent bar."""
    df = _make_candles(n=500)
    sig = _signal(
        candle_time=df.index[400].to_pydatetime(), direction="SELL",
    )
    result = bars_since_h1_extreme(sig, df)
    assert result is not None
    assert result == 0  # max high is the signal's own bar on monotonic rise


# ---------------------------------------------------------------------------
# htf_range_position_d1
# ---------------------------------------------------------------------------

def test_htf_range_position_d1_returns_bucket() -> None:
    df = _make_candles(n=500)
    # Pick a signal later in a day with enough range
    sig = _signal(
        candle_time=df.index[200].to_pydatetime(),
        entry=float(df["high"].iloc[200]),  # at the high-so-far
    )
    result = htf_range_position_d1(sig, df)
    assert result is not None
    assert result in {"LOW", "MID_LOW", "MID", "MID_HIGH", "HIGH"}
    assert type(result) is str


def test_htf_range_position_d1_none_without_candles() -> None:
    assert htf_range_position_d1(_signal(), None) is None


def test_htf_range_position_d1_none_on_small_range() -> None:
    """If intraday range < 3 pips, return None."""
    # Build a flat-day DataFrame
    idx = pd.date_range("2025-07-01 00:00", periods=50, freq="15min", tz="UTC")
    flat = pd.DataFrame(
        {
            "open":  [1.08000] * 50,
            "high":  [1.08010] * 50,  # 1 pip above
            "low":   [1.08000] * 50,
            "close": [1.08005] * 50,
        },
        index=idx,
    )
    sig = _signal(
        candle_time=flat.index[20].to_pydatetime(), entry=1.08005,
    )
    assert htf_range_position_d1(sig, flat) is None


def test_htf_range_position_d1_signal_outside_window() -> None:
    df = _make_candles(n=100)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before, entry=1.08000)
    assert htf_range_position_d1(sig, df) is None


# ---------------------------------------------------------------------------
# dist_to_prior_day_hl_atr
# ---------------------------------------------------------------------------

def test_dist_to_prior_day_hl_atr_returns_value() -> None:
    df = _make_candles(n=500)  # ~5 days of M15
    sig = _signal(
        candle_time=df.index[400].to_pydatetime(),
        entry=float(df["close"].iloc[400]),
    )
    result = dist_to_prior_day_hl_atr(sig, df)
    assert result is not None
    assert result >= 0
    assert type(result) is float


def test_dist_to_prior_day_hl_atr_none_without_candles() -> None:
    assert dist_to_prior_day_hl_atr(_signal(), None) is None


def test_dist_to_prior_day_hl_atr_no_prior_day() -> None:
    """Signal on the first available day — no prior day, return None."""
    df = _make_candles(n=40)  # ~10 hours of M15, single broker day
    sig = _signal(
        candle_time=df.index[20].to_pydatetime(), entry=1.08200,
    )
    assert dist_to_prior_day_hl_atr(sig, df) is None


def test_dist_to_prior_day_hl_atr_dtype_float() -> None:
    df = _make_candles(n=500)
    sig = _signal(
        candle_time=df.index[400].to_pydatetime(),
        entry=float(df["close"].iloc[400]),
    )
    result = dist_to_prior_day_hl_atr(sig, df)
    assert result is not None
    assert type(result) is float


# ---------------------------------------------------------------------------
# d1_trend
# ---------------------------------------------------------------------------

def _make_rising_candles(n: int = 800) -> pd.DataFrame:
    """Strong uptrend: 0.0001 drift per M15 bar."""
    return _make_candles(n=n, base_price=1.08)


def _make_declining_candles(n: int = 800) -> pd.DataFrame:
    """Strong downtrend: negative drift per M15 bar."""
    idx = pd.date_range("2025-07-01 00:00", periods=n, freq="15min", tz="UTC")
    base = 1.20
    data = {
        "open":  [base - i * 0.0001 for i in range(n)],
        "high":  [base - i * 0.0001 + 0.0010 for i in range(n)],
        "low":   [base - i * 0.0001 - 0.0005 for i in range(n)],
        "close": [base - i * 0.0001 + 0.0003 for i in range(n)],
    }
    return pd.DataFrame(data, index=idx)


def _make_flat_candles(n: int = 800) -> pd.DataFrame:
    """Nearly flat: micro-drift that stays well below 0.5 × D1 ATR."""
    idx = pd.date_range("2025-07-01 00:00", periods=n, freq="15min", tz="UTC")
    base = 1.08
    data = {
        "open":  [base + 0.000001 * i for i in range(n)],
        "high":  [base + 0.000001 * i + 0.0010 for i in range(n)],
        "low":   [base + 0.000001 * i - 0.0005 for i in range(n)],
        "close": [base + 0.000001 * i + 0.0003 for i in range(n)],
    }
    return pd.DataFrame(data, index=idx)


def test_d1_trend_rising_returns_up() -> None:
    """Strongly rising D1 closes must return 'up', not 'flat' or 'down'."""
    df = _make_rising_candles()
    sig = _signal(
        candle_time=df.index[700].to_pydatetime(),
        entry=float(df["close"].iloc[700]),
    )
    assert d1_trend(sig, df) == "up"


def test_d1_trend_declining_returns_down() -> None:
    """Strongly declining D1 closes must return 'down', not 'flat' or 'up'."""
    df = _make_declining_candles()
    sig = _signal(
        candle_time=df.index[700].to_pydatetime(),
        entry=float(df["close"].iloc[700]),
    )
    assert d1_trend(sig, df) == "down"


def test_d1_trend_flat_returns_flat() -> None:
    """Near-zero D1 delta (well under 0.5 × ATR) must return 'flat'."""
    df = _make_flat_candles()
    sig = _signal(
        candle_time=df.index[700].to_pydatetime(),
        entry=float(df["close"].iloc[700]),
    )
    assert d1_trend(sig, df) == "flat"


def test_d1_trend_returns_str_type() -> None:
    df = _make_rising_candles()
    sig = _signal(
        candle_time=df.index[700].to_pydatetime(),
        entry=float(df["close"].iloc[700]),
    )
    result = d1_trend(sig, df)
    assert type(result) is str


def test_d1_trend_none_without_candles() -> None:
    assert d1_trend(_signal(), None) is None


def test_d1_trend_insufficient_prior_days() -> None:
    """Need 5 prior D1 bars; 2 days of candles is not enough."""
    df = _make_candles(n=100)  # ~25 hours, < 5 prior days
    sig = _signal(
        candle_time=df.index[80].to_pydatetime(), entry=1.08200,
    )
    assert d1_trend(sig, df) is None


# ---------------------------------------------------------------------------
# range_bound_efficiency
# ---------------------------------------------------------------------------

def test_range_bound_efficiency_monotonic_rise() -> None:
    """Monotonic rising closes → efficiency ratio ≈ 1.0 (pure trend)."""
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[60].to_pydatetime())
    result = range_bound_efficiency(sig, df)
    assert result is not None
    assert result == pytest.approx(1.0, abs=0.01)
    assert type(result) is float


def test_range_bound_efficiency_none_without_candles() -> None:
    assert range_bound_efficiency(_signal(), None) is None


def test_range_bound_efficiency_insufficient_history() -> None:
    df = _make_candles(n=30)
    sig = _signal(candle_time=df.index[20].to_pydatetime())
    assert range_bound_efficiency(sig, df) is None


def test_range_bound_efficiency_bounded() -> None:
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[60].to_pydatetime())
    result = range_bound_efficiency(sig, df)
    assert result is not None
    assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# range_compression_ratio
# ---------------------------------------------------------------------------

def test_range_compression_ratio_returns_value() -> None:
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[50].to_pydatetime())
    result = range_compression_ratio(sig, df)
    assert result is not None
    assert result > 0
    assert type(result) is float


def test_range_compression_ratio_none_without_candles() -> None:
    assert range_compression_ratio(_signal(), None) is None


def test_range_compression_ratio_insufficient_history() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[3].to_pydatetime())
    assert range_compression_ratio(sig, df) is None


def test_range_compression_ratio_dtype_float() -> None:
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[50].to_pydatetime())
    result = range_compression_ratio(sig, df)
    assert result is not None
    assert type(result) is float


# ---------------------------------------------------------------------------
# trail_extension_atr
# ---------------------------------------------------------------------------

def test_trail_extension_atr_buy_positive_on_rising() -> None:
    """Monotonically rising closes + BUY → positive trail extension."""
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[50].to_pydatetime(), direction="BUY")
    result = trail_extension_atr(sig, df)
    assert result is not None
    assert result > 0
    assert type(result) is float


def test_trail_extension_atr_sell_negative_on_rising() -> None:
    """Rising closes but SELL → sign flips → negative extension."""
    df = _make_candles(n=100)
    sig = _signal(candle_time=df.index[50].to_pydatetime(), direction="SELL")
    result = trail_extension_atr(sig, df)
    assert result is not None
    assert result < 0


def test_trail_extension_atr_none_without_candles() -> None:
    assert trail_extension_atr(_signal(), None) is None


def test_trail_extension_atr_insufficient_history() -> None:
    df = _make_candles(n=50)
    sig = _signal(candle_time=df.index[5].to_pydatetime())
    assert trail_extension_atr(sig, df) is None


# ---------------------------------------------------------------------------
# spread_atr_ratio
# ---------------------------------------------------------------------------

def test_spread_atr_ratio_returns_value() -> None:
    df = _make_candles(n=100)
    sig = _signal(
        candle_time=df.index[50].to_pydatetime(), spread_pips=1.2,
    )
    result = spread_atr_ratio(sig, df)
    assert result is not None
    assert result > 0
    assert type(result) is float


def test_spread_atr_ratio_none_without_candles() -> None:
    assert spread_atr_ratio(_signal(), None) is None


def test_spread_atr_ratio_none_when_signal_outside_window() -> None:
    df = _make_candles(n=100)
    before = df.index[0].to_pydatetime() - pd.Timedelta(days=1)
    sig = _signal(candle_time=before)
    assert spread_atr_ratio(sig, df) is None


def test_spread_atr_ratio_scales_with_spread() -> None:
    df = _make_candles(n=100)
    low = _signal(
        candle_time=df.index[50].to_pydatetime(), spread_pips=0.5,
    )
    high = _signal(
        candle_time=df.index[50].to_pydatetime(), spread_pips=5.0,
    )
    low_r = spread_atr_ratio(low, df)
    high_r = spread_atr_ratio(high, df)
    assert low_r is not None and high_r is not None
    assert high_r > low_r


# ---------------------------------------------------------------------------
# spread_tier modification — scope broadening + DST correctness
# ---------------------------------------------------------------------------

def test_spread_tier_registered_for_fvg_impulse() -> None:
    """After broadening scope, spread_tier must appear for every strategy."""
    names_fvg = {p.name for p in get_params_for_strategy("fvg-impulse")}
    names_fvg5 = {p.name for p in get_params_for_strategy("fvg-impulse-5m")}
    names_nova = {p.name for p in get_params_for_strategy("nova-candle")}
    assert "spread_tier" in names_fvg
    assert "spread_tier" in names_fvg5
    assert "spread_tier" in names_nova


def test_spread_tier_dst_summer() -> None:
    """July in Jerusalem is IDT (+03:00). 21:00 UTC → 00:00 broker → 'H0'."""
    sig = _signal(candle_time=datetime(2025, 7, 1, 21, 0, tzinfo=timezone.utc))
    assert spread_tier(sig, None) == "H0"


def test_spread_tier_dst_summer_h1() -> None:
    """July in Jerusalem is IDT (+03:00). 22:00 UTC → 01:00 broker → 'H1'."""
    sig = _signal(candle_time=datetime(2025, 7, 1, 22, 0, tzinfo=timezone.utc))
    assert spread_tier(sig, None) == "H1"


def test_spread_tier_winter_h0() -> None:
    """January in Jerusalem is IST (+02:00). 22:00 UTC → 00:00 broker → 'H0'."""
    sig = _signal(candle_time=datetime(2025, 1, 15, 22, 0, tzinfo=timezone.utc))
    assert spread_tier(sig, None) == "H0"


def test_spread_tier_returns_h2_midday() -> None:
    sig = _signal(candle_time=datetime(2025, 7, 1, 10, 0, tzinfo=timezone.utc))
    result = spread_tier(sig, None)
    assert result == "H2"
    assert type(result) is str
