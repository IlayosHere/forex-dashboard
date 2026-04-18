"""
tests/test_fvg_impulse.py
-------------------------
Unit and integration tests for the fvg_impulse (M15) and fvg_impulse_5m (M5)
strategies: FVG detection, lifecycle helpers, trade param calculations,
scanner integration, and a smoke test for the 5m variant.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from strategies.fvg_impulse.calculations import calculate_trade_params
from strategies.fvg_impulse.data import FVG, age_and_prune_fvgs, detect_fvgs_at_bar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIP = 0.0001
SYMBOL = "EURUSD"
BASE_PRICE = 1.1000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_index(n: int, freq: str = "15min") -> pd.DatetimeIndex:
    """Create a UTC DatetimeIndex of n bars at the given frequency."""
    start = datetime(2025, 6, 10, 8, 0, tzinfo=timezone.utc)
    return pd.date_range(start, periods=n, freq=freq, tz=timezone.utc)


def _flat_ohlc(n: int, price: float = BASE_PRICE) -> pd.DataFrame:
    """Build a flat OHLC DataFrame where all prices equal price."""
    data = {
        "open": np.full(n, price),
        "high": np.full(n, price + 5 * PIP),
        "low": np.full(n, price - 5 * PIP),
        "close": np.full(n, price),
        "volume": np.ones(n),
    }
    return pd.DataFrame(data, index=_utc_index(n))


def _make_fvg(
    direction: str = "bullish",
    formation_idx: int = 2,
    near_price: float = 1.1010,
    far_price: float = 1.0990,
    age: int = 2,
) -> FVG:
    """Construct a synthetic FVG for use in isolation tests."""
    if direction == "bullish":
        top, bottom = near_price, far_price
    else:
        top, bottom = far_price, near_price
    return FVG(
        direction=direction,
        top=top,
        bottom=bottom,
        formation_idx=formation_idx,
        formation_time=datetime(2025, 6, 10, 8, 30, tzinfo=timezone.utc),
        age_bars=age,
        is_valid=True,
    )


def _signal_dict(
    direction: str = "BUY",
    close: float = 1.1020,
    fvg_far_edge: float = 1.0990,
    fvg_near_edge: float = 1.1010,
    fvg_width_pips: float = 20.0,
    broker_hour: int = 10,
) -> dict:
    """Build a minimal signal dict accepted by calculate_trade_params."""
    candle_time = datetime(2025, 6, 10, broker_hour, 0, tzinfo=timezone.utc)
    return {
        "symbol": SYMBOL,
        "direction": direction,
        "close": close,
        "fvg_far_edge": fvg_far_edge,
        "fvg_near_edge": fvg_near_edge,
        "fvg_width_pips": fvg_width_pips,
        "candle_time": candle_time,
    }


def _m15_candles_with_setup(
    fvg_near: float,
    fvg_far: float,
    direction: str,
    n: int = 10,
    freq: str = "15min",
) -> pd.DataFrame:
    """Build candles with a pre-formed virgin FVG and a wick-test signal candle.

    Layout (indices 0..n-1):
    - Bar 0 (C0): creates the gap boundary on the far side
    - Bar 1 (C1): middle bar — quiet, must not violate the gap
    - Bar 2 (C2): FVG-forming bar — creates gap vs bar 0
    - Bars 3..(n-3): quiet, stay well clear of the near edge (FVG stays virgin)
    - Bar n-2 (last_closed): wick-tests the FVG near edge, close stays outside
    - Bar n-1: current forming bar (its timestamp equals fake_now boundary)

    For bullish FVGs the quiet bars sit above the near_edge so they never touch it.
    For bearish FVGs the quiet bars sit below the near_edge.
    """
    idx = _utc_index(n, freq=freq)

    if direction == "bullish":
        # Quiet bars above the near edge — well clear of the gap
        quiet = fvg_near + 10 * PIP
        opens = np.full(n, quiet)
        highs = np.full(n, quiet + 5 * PIP)
        lows = np.full(n, quiet - 2 * PIP)    # stay above near_edge
        closes = np.full(n, quiet)

        # C0: high below fvg_far so gap can exist (C0.high < C2.low)
        highs[0] = fvg_far - PIP
        lows[0] = fvg_far - 5 * PIP
        closes[0] = fvg_far - 2 * PIP
        opens[0] = fvg_far - 2 * PIP

        # C1: middle bar — must not bridge the gap
        lows[1] = fvg_near + 5 * PIP
        highs[1] = fvg_near + 12 * PIP
        closes[1] = fvg_near + 8 * PIP
        opens[1] = fvg_near + 8 * PIP

        # C2: low above fvg_near, confirming the gap
        lows[2] = fvg_near + PIP
        highs[2] = fvg_near + 10 * PIP
        closes[2] = fvg_near + 5 * PIP
        opens[2] = fvg_near + 5 * PIP

        # Signal candle: wick dips into FVG, close stays above near_edge
        s = n - 2
        lows[s] = fvg_near - 2 * PIP    # wick enters the gap
        closes[s] = fvg_near + 3 * PIP  # close stays outside (above)
        opens[s] = fvg_near + 3 * PIP
        highs[s] = fvg_near + 8 * PIP
    else:
        # bearish: quiet bars below the near edge
        quiet = fvg_near - 10 * PIP
        opens = np.full(n, quiet)
        highs = np.full(n, quiet + 2 * PIP)   # stay below near_edge
        lows = np.full(n, quiet - 5 * PIP)
        closes = np.full(n, quiet)

        # C0: low above fvg_far (C0.low > C2.high)
        lows[0] = fvg_far + PIP
        highs[0] = fvg_far + 5 * PIP
        closes[0] = fvg_far + 2 * PIP
        opens[0] = fvg_far + 2 * PIP

        # C1: middle bar — must not bridge the gap
        highs[1] = fvg_near - 5 * PIP
        lows[1] = fvg_near - 12 * PIP
        closes[1] = fvg_near - 8 * PIP
        opens[1] = fvg_near - 8 * PIP

        # C2: high below fvg_near, confirming the gap
        highs[2] = fvg_near - PIP
        lows[2] = fvg_near - 10 * PIP
        closes[2] = fvg_near - 5 * PIP
        opens[2] = fvg_near - 5 * PIP

        # Signal candle: wick rises into FVG, close stays below near_edge
        s = n - 2
        highs[s] = fvg_near + 2 * PIP   # wick enters the gap
        closes[s] = fvg_near - 3 * PIP  # close stays outside (below)
        opens[s] = fvg_near - 3 * PIP
        lows[s] = fvg_near - 8 * PIP

    volumes = np.ones(n)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


# ---------------------------------------------------------------------------
# 1. FVG detection unit tests
# ---------------------------------------------------------------------------


def test_detect_fvgs_bullish_gap_up() -> None:
    """detect_fvgs_at_bar detects a bullish FVG when C0.high < C2.low."""
    df = _flat_ohlc(5)
    h = df["high"].values.copy()
    l = df["low"].values.copy()

    # Create gap: C0 high = 1.1002, C2 low = 1.1008 (gap above C0)
    h[0] = BASE_PRICE + 2 * PIP
    l[2] = BASE_PRICE + 8 * PIP

    fvgs: list[FVG] = []
    detect_fvgs_at_bar(fvgs, h, l, i=2, candles=df)

    bullish = [f for f in fvgs if f.direction == "bullish"]
    assert len(bullish) == 1
    assert bullish[0].top == pytest.approx(l[2])
    assert bullish[0].bottom == pytest.approx(h[0])
    assert bullish[0].formation_idx == 2


def test_detect_fvgs_bearish_gap_down() -> None:
    """detect_fvgs_at_bar detects a bearish FVG when C0.low > C2.high."""
    df = _flat_ohlc(5)
    h = df["high"].values.copy()
    l = df["low"].values.copy()

    # Create gap: C0 low = 1.1008, C2 high = 1.1002 (gap below C0)
    l[0] = BASE_PRICE + 8 * PIP
    h[2] = BASE_PRICE + 2 * PIP

    fvgs: list[FVG] = []
    detect_fvgs_at_bar(fvgs, h, l, i=2, candles=df)

    bearish = [f for f in fvgs if f.direction == "bearish"]
    assert len(bearish) == 1
    assert bearish[0].top == pytest.approx(l[0])
    assert bearish[0].bottom == pytest.approx(h[2])
    assert bearish[0].formation_idx == 2


def test_detect_fvgs_no_gap_returns_empty() -> None:
    """detect_fvgs_at_bar returns no FVGs when C0 and C2 overlap."""
    df = _flat_ohlc(5)
    h = df["high"].values.copy()
    l = df["low"].values.copy()

    # Overlapping candles: no gap in either direction
    h[0] = BASE_PRICE + 10 * PIP
    l[0] = BASE_PRICE - 10 * PIP
    h[2] = BASE_PRICE + 8 * PIP
    l[2] = BASE_PRICE - 8 * PIP

    fvgs: list[FVG] = []
    detect_fvgs_at_bar(fvgs, h, l, i=2, candles=df)

    assert fvgs == []


# ---------------------------------------------------------------------------
# 2. age_and_prune_fvgs unit tests
# ---------------------------------------------------------------------------


def test_age_and_prune_wick_through_near_edge_bullish() -> None:
    """Bullish FVG becomes invalid when price wicks below the near edge."""
    fvg = _make_fvg(direction="bullish", near_price=1.1010, far_price=1.0990, age=1)
    n = 5
    h = np.full(n, BASE_PRICE + 5 * PIP)
    l = np.full(n, BASE_PRICE - 5 * PIP)
    c = np.full(n, BASE_PRICE)

    # Bar 4: wick dips below near_edge (1.1010), close stays outside
    l[4] = fvg.near_edge - PIP
    c[4] = fvg.near_edge + 2 * PIP   # close remains above (but virgin check fires)

    age_and_prune_fvgs([fvg], h, l, c, i=4)

    assert fvg.is_valid is False


def test_age_and_prune_close_past_far_edge_bullish() -> None:
    """Bullish FVG becomes invalid when price closes below the far edge."""
    fvg = _make_fvg(direction="bullish", near_price=1.1010, far_price=1.0990, age=1)
    n = 5
    h = np.full(n, BASE_PRICE + 5 * PIP)
    l = np.full(n, BASE_PRICE - 5 * PIP)
    c = np.full(n, BASE_PRICE)

    # Bar 4: close below far_edge (1.0990) — consumption
    c[4] = fvg.far_edge - 5 * PIP
    l[4] = fvg.far_edge - 10 * PIP

    age_and_prune_fvgs([fvg], h, l, c, i=4)

    assert fvg.is_valid is False


def test_age_and_prune_formation_bar_is_skipped() -> None:
    """FVG at its own formation_idx is not aged or invalidated."""
    fvg = _make_fvg(direction="bullish", formation_idx=3, age=0)
    n = 5
    h = np.full(n, BASE_PRICE + 5 * PIP)
    l = np.full(n, BASE_PRICE - 5 * PIP)
    c = np.full(n, BASE_PRICE)

    age_and_prune_fvgs([fvg], h, l, c, i=3)

    assert fvg.age_bars == 0
    assert fvg.is_valid is True


def test_age_and_prune_bearish_wick_above_near_edge() -> None:
    """Bearish FVG becomes invalid when price wicks above its near edge."""
    fvg = _make_fvg(direction="bearish", near_price=1.0990, far_price=1.1010, age=1)
    n = 5
    h = np.full(n, BASE_PRICE + 5 * PIP)
    l = np.full(n, BASE_PRICE - 5 * PIP)
    c = np.full(n, BASE_PRICE)

    # Bar 4: wick above near_edge (1.0990) for bearish FVG
    h[4] = fvg.near_edge + PIP

    age_and_prune_fvgs([fvg], h, l, c, i=4)

    assert fvg.is_valid is False


# ---------------------------------------------------------------------------
# 3. calculate_trade_params unit tests
# ---------------------------------------------------------------------------


def test_calculate_trade_params_returns_required_keys() -> None:
    """Returns dict with sl, tp, lot_size, risk_pips, spread_pips for valid input."""
    result = calculate_trade_params(_signal_dict())

    assert result is not None
    assert {"sl", "tp", "lot_size", "risk_pips", "spread_pips"} <= result.keys()


def test_calculate_trade_params_returns_none_when_risk_zero() -> None:
    """Returns None when effective_risk_pips <= 0 (entry equals far edge)."""
    sig = _signal_dict(direction="BUY", close=1.1020)
    # Move far_edge so close to entry that SL is above entry (impossible trade)
    sig["fvg_far_edge"] = 1.1025   # far_edge > close for BUY => SL > entry
    result = calculate_trade_params(sig)

    assert result is None


def test_calculate_trade_params_buy_sl_below_tp_above_entry() -> None:
    """BUY: SL must be below entry, TP must be above entry."""
    sig = _signal_dict(direction="BUY", close=1.1020, fvg_far_edge=1.0990)
    result = calculate_trade_params(sig)

    assert result is not None
    assert result["sl"] < sig["close"]
    assert result["tp"] > sig["close"]


def test_calculate_trade_params_sell_sl_above_tp_below_entry() -> None:
    """SELL: SL must be above entry, TP must be below entry."""
    sig = _signal_dict(
        direction="SELL",
        close=1.0980,
        fvg_far_edge=1.1010,
        fvg_near_edge=1.0990,
    )
    result = calculate_trade_params(sig)

    assert result is not None
    assert result["sl"] > sig["close"]
    assert result["tp"] < sig["close"]


def test_calculate_trade_params_lot_size_positive() -> None:
    """lot_size must be a positive float >= 0.01."""
    result = calculate_trade_params(_signal_dict())

    assert result is not None
    assert result["lot_size"] >= 0.01


# ---------------------------------------------------------------------------
# 4. Scanner integration tests (scan_symbol)
# ---------------------------------------------------------------------------

NEAR_EDGE_BULL = 1.1010
FAR_EDGE_BULL = 1.0990
N_BARS = 10
FREQ_15 = "15min"


def _freeze_now_at_bar(df: pd.DataFrame, bar_index: int, freq_minutes: int = 15) -> datetime:
    """Return a fake 'now' that makes bar_index the last *closed* bar.

    The scanner computes the current boundary by truncating now.minute to the
    nearest freq_minutes boundary and requires candle_time < boundary.  To
    ensure bar_index satisfies that check we place fake_now 2 minutes after
    the *next* boundary: bar_index.timestamp + freq_minutes + 2 minutes.
    """
    bar_ts = df.index[bar_index].to_pydatetime()
    return bar_ts + timedelta(minutes=freq_minutes + 2)


def test_scan_symbol_no_signal_when_no_wick_test() -> None:
    """scan_symbol returns empty list when last candle does not wick-test any FVG."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    df = _flat_ohlc(N_BARS)
    fake_now = _freeze_now_at_bar(df, N_BARS - 2)

    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scanner.scan_symbol(df, SYMBOL)

    assert result == []


def test_scan_symbol_returns_signal_on_valid_wick_test() -> None:
    """scan_symbol returns a signal dict when a wick-test occurs on last closed bar."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    df = _m15_candles_with_setup(
        fvg_near=NEAR_EDGE_BULL,
        fvg_far=FAR_EDGE_BULL,
        direction="bullish",
        n=N_BARS,
    )
    last_closed_idx = N_BARS - 2
    fake_now = _freeze_now_at_bar(df, last_closed_idx)

    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scanner.scan_symbol(df, SYMBOL)

    assert len(result) >= 1
    sig = result[0]
    assert sig["symbol"] == SYMBOL
    assert sig["direction"] == "BUY"
    assert "sl" in sig
    assert "tp" in sig
    assert "lot_size" in sig


def test_scan_symbol_dedup_skips_alerted_candle() -> None:
    """scan_symbol skips candles already in _alerted_candles."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    df = _m15_candles_with_setup(
        fvg_near=NEAR_EDGE_BULL,
        fvg_far=FAR_EDGE_BULL,
        direction="bullish",
        n=N_BARS,
    )
    last_closed_idx = N_BARS - 2
    candle_time = df.index[last_closed_idx].to_pydatetime()
    scanner._alerted_candles.add((SYMBOL, candle_time))

    fake_now = _freeze_now_at_bar(df, last_closed_idx)

    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scanner.scan_symbol(df, SYMBOL)

    assert result == []


def test_scan_symbol_signal_has_all_required_fields() -> None:
    """Signal dict from scan_symbol contains all fields needed by _to_signal."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    required_keys = {
        "symbol", "direction", "candle_time", "entry_price",
        "sl", "tp", "lot_size", "risk_pips", "spread_pips",
        "fvg_near_edge", "fvg_far_edge", "fvg_width_pips",
        "fvg_age", "fvg_formation_time",
    }

    df = _m15_candles_with_setup(
        fvg_near=NEAR_EDGE_BULL,
        fvg_far=FAR_EDGE_BULL,
        direction="bullish",
        n=N_BARS,
    )
    last_closed_idx = N_BARS - 2
    fake_now = _freeze_now_at_bar(df, last_closed_idx)

    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scanner.scan_symbol(df, SYMBOL)

    assert len(result) >= 1
    assert required_keys <= result[0].keys()


# ---------------------------------------------------------------------------
# 5. scan() integration — mocked get_candles
# ---------------------------------------------------------------------------


def test_scan_returns_signal_list_with_mocked_candles() -> None:
    """scan() returns list[Signal] objects when a valid setup is mocked."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    df = _m15_candles_with_setup(
        fvg_near=NEAR_EDGE_BULL,
        fvg_far=FAR_EDGE_BULL,
        direction="bullish",
        n=N_BARS,
    )
    last_closed_idx = N_BARS - 2
    fake_now = _freeze_now_at_bar(df, last_closed_idx)

    # scan() checks now.minute % 15 < 5 to decide whether to run
    fake_now_run = fake_now.replace(minute=2)

    with (
        patch("strategies.fvg_impulse.scanner.datetime") as mock_dt,
        patch("strategies.fvg_impulse.data.get_candles", return_value=df),
        patch("strategies.fvg_impulse.scanner.scan_all_symbols") as mock_scan_all,
    ):
        mock_dt.now.return_value = fake_now_run
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        mock_scan_all.return_value = [
            {
                "symbol": SYMBOL,
                "direction": "BUY",
                "fvg_near_edge": NEAR_EDGE_BULL,
                "fvg_far_edge": FAR_EDGE_BULL,
                "fvg_width_pips": 20.0,
                "fvg_age": 3,
                "fvg_formation_time": datetime(2025, 6, 10, 8, 30, tzinfo=timezone.utc),
                "candle_time": df.index[last_closed_idx].to_pydatetime(),
                "entry_price": 1.1015,
                "sl": 1.0987,
                "tp": 1.1043,
                "lot_size": 0.45,
                "risk_pips": 28.0,
                "spread_pips": 0.2,
            }
        ]

        signals = scanner.scan()

    assert len(signals) == 1
    assert signals[0].strategy == "fvg-impulse"
    assert signals[0].symbol == SYMBOL
    assert signals[0].lot_size > 0


def test_scan_returns_empty_off_boundary() -> None:
    """scan() returns empty list when not within first 5 minutes of a 15-min window."""
    from strategies.fvg_impulse import scanner

    scanner._alerted_candles.clear()

    off_boundary = datetime(2025, 6, 10, 10, 7, tzinfo=timezone.utc)

    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = off_boundary
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = scanner.scan()

    assert result == []


# ---------------------------------------------------------------------------
# 6. fvg_impulse_5m smoke test
# ---------------------------------------------------------------------------

NEAR_EDGE_5M = 1.1010
FAR_EDGE_5M = 1.0990
N_BARS_5M = 10


def test_fvg_impulse_5m_scan_returns_correct_strategy_slug() -> None:
    """5m scan() returns Signal with strategy='fvg-impulse-5m' and lot_size > 0."""
    from strategies.fvg_impulse_5m import scanner as scanner_5m

    scanner_5m._alerted_candles.clear()

    df = _m15_candles_with_setup(
        fvg_near=NEAR_EDGE_5M,
        fvg_far=FAR_EDGE_5M,
        direction="bullish",
        n=N_BARS_5M,
        freq="5min",
    )
    last_closed_idx = N_BARS_5M - 2
    candle_time = df.index[last_closed_idx].to_pydatetime()
    fake_raw_signal = {
        "symbol": SYMBOL,
        "direction": "BUY",
        "fvg_near_edge": NEAR_EDGE_5M,
        "fvg_far_edge": FAR_EDGE_5M,
        "fvg_width_pips": 20.0,
        "fvg_age": 3,
        "fvg_formation_time": datetime(2025, 6, 10, 8, 30, tzinfo=timezone.utc),
        "candle_time": candle_time,
        "entry_price": 1.1015,
        "sl": 1.0987,
        "tp": 1.1043,
        "lot_size": 0.45,
        "risk_pips": 28.0,
        "spread_pips": 0.2,
    }

    with patch(
        "strategies.fvg_impulse_5m.scanner.scan_all_symbols",
        return_value=[fake_raw_signal],
    ):
        signals = scanner_5m.scan()

    assert len(signals) == 1
    sig = signals[0]
    assert sig.strategy == "fvg-impulse-5m"
    assert sig.lot_size > 0
    assert sig.symbol == SYMBOL
