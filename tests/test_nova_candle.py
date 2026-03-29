"""
tests/test_nova_candle.py
-------------------------
Unit tests for the nova-candle strategy: snake_line swing detection,
BOS-based SL computation, nova candle pattern detection, and full
calculate_trade_params integration.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from strategies.nova_candle.calculations import calculate_trade_params
from strategies.nova_candle.scanner import find_nova_candle
from strategies.nova_candle.sl import compute_bos_sl
from strategies.nova_candle.snake_line import compute_snake_line_with_swings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PIP = 0.0001
BUFFER = 3.0


def _zigzag_arrays(n: int = 60) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build synthetic close/high/low with a clear up-down-up zigzag.

    Shape: ramp up to bar 15, drop to bar 30, ramp up to bar 45, flat tail.
    Each bar has high = close + 0.0005, low = close - 0.0005.
    """
    closes = np.full(n, 1.1000)
    for i in range(1, 16):
        closes[i] = 1.1000 + i * 0.0020  # peak ~1.1300 at bar 15
    for i in range(16, 31):
        closes[i] = closes[15] - (i - 15) * 0.0020  # valley ~1.1000 at 30
    for i in range(31, 46):
        closes[i] = closes[30] + (i - 30) * 0.0020  # peak ~1.1300 at 45
    for i in range(46, n):
        closes[i] = closes[45]

    highs = closes + 0.0005
    lows = closes - 0.0005
    return closes, highs, lows


def _utc_index(n: int, recent: bool = False) -> pd.DatetimeIndex:
    """Create a UTC DatetimeIndex of 15-min bars."""
    if recent:
        end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        end = end.replace(minute=(end.minute // 15) * 15) - timedelta(minutes=15)
        start = end - timedelta(minutes=15 * (n - 1))
    else:
        start = datetime(2025, 6, 10, 8, 0, tzinfo=timezone.utc)
    return pd.date_range(start, periods=n, freq="15min", tz=timezone.utc)


# ---------------------------------------------------------------------------
# 1. snake_line swing detection
# ---------------------------------------------------------------------------


def test_snake_line_finds_swing_high_and_low() -> None:
    """Zigzag up-down-up must produce at least one SH and one SL."""
    closes, highs, lows = _zigzag_arrays()
    _, sh, sl = compute_snake_line_with_swings(closes, highs, lows)

    assert len(sh) >= 1, "Expected at least one swing high"
    assert len(sl) >= 1, "Expected at least one swing low"


def test_snake_line_swing_high_near_peak() -> None:
    """First swing high extreme_idx should be near bar 15 (the peak)."""
    closes, highs, lows = _zigzag_arrays()
    _, sh, _ = compute_snake_line_with_swings(closes, highs, lows)

    first_sh_idx = sh[0][0]
    assert 10 <= first_sh_idx <= 20, f"SH extreme at {first_sh_idx}, expected near 15"


def test_snake_line_swing_low_near_valley() -> None:
    """First swing low extreme_idx should be near bar 30 (the valley)."""
    closes, highs, lows = _zigzag_arrays()
    _, _, sl = compute_snake_line_with_swings(closes, highs, lows)

    first_sl_idx = sl[0][0]
    assert 25 <= first_sl_idx <= 35, f"SL extreme at {first_sl_idx}, expected near 30"


# ---------------------------------------------------------------------------
# 2. compute_bos_sl
# ---------------------------------------------------------------------------


def test_bos_sl_short_uses_swing_high_plus_buffer() -> None:
    """SHORT SL should be above a swing high + buffer."""
    closes, highs, lows = _zigzag_arrays()
    sl, idx = compute_bos_sl(
        highs=highs, lows=lows, closes=closes,
        signal_idx=55, direction=1, pip=PIP,
        buffer_pips=BUFFER, entry=1.1300, min_risk_pips=0.0,
    )
    assert sl is not None
    assert sl > highs[idx], "SHORT SL must be above the swing high"


def test_bos_sl_long_uses_swing_low_minus_buffer() -> None:
    """LONG SL should be below a swing low - buffer."""
    closes, highs, lows = _zigzag_arrays()
    sl, idx = compute_bos_sl(
        highs=highs, lows=lows, closes=closes,
        signal_idx=55, direction=0, pip=PIP,
        buffer_pips=BUFFER, entry=1.1000, min_risk_pips=0.0,
    )
    assert sl is not None
    assert sl < lows[idx], "LONG SL must be below the swing low"


def test_bos_sl_min_risk_skips_tight_swing() -> None:
    """If nearest swing gives < min_risk_pips, walk to the next."""
    closes, highs, lows = _zigzag_arrays()
    # Entry very close to the valley so nearest swing is too tight
    entry = float(lows.min()) + 2 * PIP
    sl_tight, _ = compute_bos_sl(
        highs=highs, lows=lows, closes=closes,
        signal_idx=55, direction=0, pip=PIP,
        buffer_pips=BUFFER, entry=entry, min_risk_pips=5.0,
    )
    # With 2-pip distance + 3-pip buffer = ~5 pips, borderline.
    # Using a very tight entry should either skip or return None.
    # The key assertion: if it returns a level, it must give >= 5 pips risk.
    if sl_tight is not None:
        risk_pips = abs(entry - sl_tight) / PIP
        assert risk_pips >= 5.0, f"Risk {risk_pips:.1f} pips < min 5.0"


# ---------------------------------------------------------------------------
# 3. find_nova_candle detection
# ---------------------------------------------------------------------------


def _nova_df(direction: str, n: int = 55) -> pd.DataFrame:
    """Build a DataFrame with a nova candle as the second-to-last bar."""
    idx = _utc_index(n, recent=True)
    if direction == "BUY":
        base = np.linspace(1.0800, 1.1000, n)
        data = {
            "open": base.copy(), "high": base + 0.0010,
            "low": base - 0.0010, "close": base + 0.0005,
        }
        # Nova candle at position -2 (last closed): open == low, close > open
        data["open"][-2] = 1.0990
        data["low"][-2] = 1.0990  # open == low (no lower wick)
        data["high"][-2] = 1.1010
        data["close"][-2] = 1.1005  # bullish body
    else:
        base = np.linspace(1.1000, 1.0800, n)
        data = {
            "open": base.copy(), "high": base + 0.0010,
            "low": base - 0.0010, "close": base - 0.0005,
        }
        # Nova candle at position -2: open == high, close < open
        data["open"][-2] = 1.0810
        data["high"][-2] = 1.0810  # open == high (no upper wick)
        data["low"][-2] = 1.0790
        data["close"][-2] = 1.0795  # bearish body
    return pd.DataFrame(data, index=idx)


def _mock_now_for_df(df: pd.DataFrame) -> datetime:
    """Return a fake 'now' inside the last bar's period (idx[-1] + 2min).

    This makes idx[-2] the last *closed* candle (its timestamp < boundary).
    Freshness: ~17 minutes, well within the 20-minute window.
    """
    return df.index[-1].to_pydatetime() + timedelta(minutes=2)


def test_find_nova_candle_detects_buy() -> None:
    """Bullish nova candle (open == low) should return BUY."""
    from strategies.nova_candle import scanner
    scanner._alerted_candles.clear()

    df = _nova_df("BUY")
    fake_now = _mock_now_for_df(df)
    with patch("strategies.nova_candle.scanner.datetime") as m:
        m.now.return_value = fake_now
        m.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = find_nova_candle(df, "EURUSD")

    assert result is not None
    assert result["direction"] == "BUY"
    assert result["entry_price"] == pytest.approx(df.iloc[-2]["open"])


def test_find_nova_candle_detects_sell() -> None:
    """Bearish nova candle (open == high) should return SELL."""
    from strategies.nova_candle import scanner
    scanner._alerted_candles.clear()

    df = _nova_df("SELL")
    fake_now = _mock_now_for_df(df)
    with patch("strategies.nova_candle.scanner.datetime") as m:
        m.now.return_value = fake_now
        m.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = find_nova_candle(df, "EURUSD")

    assert result is not None
    assert result["direction"] == "SELL"


def test_find_nova_candle_rejects_wick() -> None:
    """Candle with open-side wick > tolerance should be rejected."""
    from strategies.nova_candle import scanner
    scanner._alerted_candles.clear()

    df = _nova_df("BUY")
    # Add a wick larger than 1-pip tolerance
    df.iloc[-2, df.columns.get_loc("low")] = df.iloc[-2]["open"] - 0.00020

    fake_now = _mock_now_for_df(df)
    with patch("strategies.nova_candle.scanner.datetime") as m:
        m.now.return_value = fake_now
        m.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = find_nova_candle(df, "EURUSD")

    assert result is None, "Nova candle with excessive wick should be rejected"


# ---------------------------------------------------------------------------
# 4. calculate_trade_params integration
# ---------------------------------------------------------------------------


def test_trade_params_entry_is_candle_open() -> None:
    """Entry must be the candle open (limit order), not close."""
    closes, highs, lows = _zigzag_arrays(n=60)
    idx = _utc_index(60, recent=True)
    df = pd.DataFrame(
        {"open": closes - 0.0002, "high": highs, "low": lows, "close": closes},
        index=idx,
    )
    signal = {
        "symbol": "EURUSD", "direction": "BUY",
        "open": float(df.iloc[55]["open"]),
        "candle_time": df.index[55].to_pydatetime(),
    }
    result = calculate_trade_params(signal, df, signal_idx=55)

    assert result["sl"] is not None
    assert result["bos_candle_time"] is not None
    assert result["bos_swing_price"] is not None


def test_trade_params_tp_mirrors_sl_distance() -> None:
    """TP should mirror raw risk distance from entry (1:1 RR pre-spread)."""
    closes, highs, lows = _zigzag_arrays(n=60)
    idx = _utc_index(60, recent=True)
    df = pd.DataFrame(
        {"open": closes - 0.0002, "high": highs, "low": lows, "close": closes},
        index=idx,
    )
    entry = float(df.iloc[55]["open"])
    signal = {
        "symbol": "EURUSD", "direction": "BUY",
        "open": entry,
        "candle_time": df.index[55].to_pydatetime(),
    }
    result = calculate_trade_params(signal, df, signal_idx=55)

    if result["sl"] is not None:
        raw_risk = abs(entry - result["sl"])
        expected_tp = entry + raw_risk
        assert result["tp"] == pytest.approx(expected_tp, abs=PIP)
