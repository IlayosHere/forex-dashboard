"""
strategies/fvg_impulse_5m/scanner.py - Virgin FVG wick-test scanner (M5).

Fetches 70 M5 candles per symbol, detects FVGs, tracks virginity,
and checks the last closed candle for wick-test rejection signals.

No gates -- bare-bones: virgin FVG + wick into + close outside.

Plugin interface
----------------
scan() -> list[Signal]   <- called by the runner every 5 minutes
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from shared.calculator import pip_size
from shared.signal import Signal

from .calculations import calculate_midpoint_sl, calculate_trade_params
from .data import FVG, age_and_prune_fvgs, detect_fvgs_at_bar, get_candles

logger = logging.getLogger(__name__)

# Dedup: set of (symbol, candle_time) to prevent duplicate alerts within a cycle
_alerted_candles: set = set()

DEFAULT_PAIRS = "EURUSD,AUDUSD,NZDUSD,USDJPY,USDCHF,USDCAD,GBPUSD,EURJPY,GBPJPY,EURGBP,AUDJPY"


# ---------------------------------------------------------------------------
# FVG detection and signal scanning
# ---------------------------------------------------------------------------

def _find_last_closed_index(candles: pd.DataFrame) -> int | None:
    """Find index of last closed candle (before current 5-min boundary)."""
    now = datetime.now(timezone.utc)
    current_boundary = now.replace(
        minute=(now.minute // 5) * 5, second=0, microsecond=0,
    )
    for i in range(len(candles) - 1, -1, -1):
        ct = candles.index[i].to_pydatetime()
        if ct < current_boundary:
            return i
    return None


def scan_symbol(candles: pd.DataFrame, symbol: str) -> list[dict[str, Any]]:
    """Scan one symbol's candles for virgin FVG wick-test signals.

    Rebuilds FVG state from scratch each cycle. Checks only the last
    closed candle for signals.

    Returns list of signal dicts (usually 0 or 1, but a candle can
    wick-test multiple FVGs).
    """
    if len(candles) < 3:
        return []

    last_idx = _find_last_closed_index(candles)
    if last_idx is None or last_idx < 2:
        return []

    # Only alert on fresh candles (closed within last 8 minutes)
    now = datetime.now(timezone.utc)
    candle_time = candles.index[last_idx].to_pydatetime()
    if now - candle_time > timedelta(minutes=8):
        return []

    # Dedup check
    candle_key = (symbol, candle_time)
    if candle_key in _alerted_candles:
        return []

    pip = pip_size(symbol)
    h = candles["high"].values
    l = candles["low"].values
    c = candles["close"].values
    o = candles["open"].values

    # --- Build FVG list from history (stop BEFORE signal candle) ---
    # The signal candle's wick touches the near edge -- that IS the signal.
    # If we process it in the lifecycle loop, the virgin check kills the
    # FVG before we can detect the wick-test.
    fvgs: list[FVG] = []

    for i in range(2, last_idx):
        detect_fvgs_at_bar(fvgs, h, l, i, candles)
        age_and_prune_fvgs(fvgs, h, l, c, i)

    # Also detect FVGs that form on the signal candle itself (they'll
    # have age=0 and be skipped for signals, but will be valid next cycle)
    if last_idx >= 2:
        detect_fvgs_at_bar(fvgs, h, l, last_idx, candles)

    # --- Check last closed candle for wick-test signals ---
    fvgs = [f for f in fvgs if f.is_valid]
    signals = _check_wick_tests(
        fvgs, h, l, c, o, last_idx, candle_time, symbol, pip,
    )

    if signals:
        _alerted_candles.add(candle_key)

    return signals


def _check_wick_tests(
    fvgs: list[FVG],
    h: Any, l: Any, c: Any, o: Any,
    last_idx: int,
    candle_time: datetime,
    symbol: str,
    pip: float,
) -> list[dict[str, Any]]:
    """Check the last closed candle for wick-test signals against valid FVGs."""
    signals: list[dict] = []
    bar_high = float(h[last_idx])
    bar_low = float(l[last_idx])
    bar_close = float(c[last_idx])
    bar_open = float(o[last_idx])

    for fvg in fvgs:
        if fvg.formation_idx == last_idx:
            continue

        # Wick-test: wick enters zone, close stays outside
        is_test = False
        if fvg.direction == "bullish":
            is_test = bar_low < fvg.near_edge and bar_close > fvg.near_edge
        else:
            is_test = bar_high > fvg.near_edge and bar_close < fvg.near_edge

        if not is_test:
            continue

        direction = "BUY" if fvg.direction == "bullish" else "SELL"
        width_pips = fvg.height / pip

        logger.info(
            "%s FVG signal @ %s: %s near=%.5f far=%.5f width=%.1fpip age=%d",
            direction, candle_time.strftime("%H:%M"), symbol,
            fvg.near_edge, fvg.far_edge, width_pips, fvg.age_bars,
        )

        sig = {
            "symbol": symbol,
            "direction": direction,
            "fvg_near_edge": fvg.near_edge,
            "fvg_far_edge": fvg.far_edge,
            "fvg_width_pips": round(width_pips, 1),
            "fvg_age": fvg.age_bars,
            "fvg_formation_time": fvg.formation_time,
            "candle_time": candle_time,
            "entry_price": bar_close,
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
        }
        trade_params = calculate_trade_params(sig)
        if trade_params is None:
            continue
        sig.update(trade_params)
        sl_mid = calculate_midpoint_sl(sig)
        if sl_mid is not None:
            sig["sl_midpoint"] = sl_mid
            sig["tp_midpoint"] = 2 * bar_close - sl_mid
        signals.append(sig)

    return signals


# ---------------------------------------------------------------------------
# Scan all symbols
# ---------------------------------------------------------------------------

def scan_all_symbols(symbols: list[str]) -> list[dict[str, Any]]:
    """Scan all symbols for virgin FVG wick-test signals."""
    now = datetime.now(timezone.utc)
    _alerted_candles.difference_update(
        {(s, t) for s, t in _alerted_candles if now - t > timedelta(minutes=15)}
    )

    signals: list[dict] = []
    delay = 2  # seconds between TradingView requests

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(delay)
        candles = get_candles(symbol)
        if candles is None:
            continue

        result = scan_symbol(candles, symbol)
        signals.extend(result)

    return signals


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def _to_signal(raw: dict[str, Any]) -> Signal:
    """Map a raw signal dict to the shared Signal dataclass."""
    return Signal(
        strategy="fvg-impulse-5m",
        symbol=raw["symbol"],
        direction=raw["direction"],
        candle_time=raw["candle_time"],
        entry=raw["entry_price"],
        sl=raw["sl"],
        tp=raw["tp"],
        lot_size=raw["lot_size"],
        risk_pips=raw["risk_pips"],
        spread_pips=raw["spread_pips"],
        metadata={
            "fvg_near_edge": raw["fvg_near_edge"],
            "fvg_far_edge": raw["fvg_far_edge"],
            "fvg_width_pips": raw["fvg_width_pips"],
            "fvg_age": raw["fvg_age"],
            "fvg_formation_time": raw["fvg_formation_time"].isoformat(),
            **({"sl_midpoint": raw["sl_midpoint"], "tp_midpoint": raw["tp_midpoint"]} if raw.get("sl_midpoint") is not None else {}),
        },
    )


def scan() -> list[Signal]:
    """Strategy plugin entry point. Called by the runner every 5 minutes.

    Reads FVG_IMPULSE_5M_PAIRS env var (comma-separated) or falls back to
    the 11 default pairs.
    """
    symbols = [
        p.strip()
        for p in os.getenv("FVG_IMPULSE_5M_PAIRS", DEFAULT_PAIRS).split(",")
        if p.strip()
    ]
    raw_signals = scan_all_symbols(symbols)
    return [_to_signal(s) for s in raw_signals]
