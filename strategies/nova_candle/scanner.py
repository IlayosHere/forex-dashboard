"""
strategies/nova_candle/scanner.py - Nova (wickless) momentum candle scanner.

Fetches 70 M15 candles per symbol via tvDatafeed (TradingView) and checks
for nova candles: no wick on the open side (open == low for bullish,
open == high for bearish).

Plugin interface
----------------
scan() -> list[Signal]   <- called by the runner every 15 minutes
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from shared.signal import Signal
from strategies.fvg_impulse.data import get_candles

from .calculations import calculate_trade_params

logger = logging.getLogger(__name__)

# Already-alerted candles: set of (symbol, candle_time) to prevent duplicate alerts
_alerted_candles: set = set()

DEFAULT_PAIRS = "EURUSD,AUDUSD,NZDUSD,USDJPY,USDCHF,USDCAD,GBPUSD"


# ---------------------------------------------------------------------------
# Nova (wickless momentum) candle detection
# ---------------------------------------------------------------------------

def _find_last_closed_index(candles: pd.DataFrame) -> int | None:
    """Find the index of the last closed candle (before current 15-min boundary)."""
    now = datetime.now(timezone.utc)
    current_boundary = now.replace(
        minute=(now.minute // 15) * 15, second=0, microsecond=0,
    )
    for i in range(len(candles) - 1, -1, -1):
        ct = candles.index[i].to_pydatetime()
        if ct < current_boundary:
            return i
    return None


def find_nova_candle(
    candles: pd.DataFrame,
    symbol: str = "",
) -> dict[str, Any] | None:
    """
    Inspect the last closed candle for a Nova (wickless momentum) pattern.

    Criteria:
    1. No open-side wick (open == low for bullish, open == high for bearish)

    Returns dict with signal info or None.
    """
    if len(candles) < 2:
        return None

    idx = _find_last_closed_index(candles)
    if idx is None:
        return None

    c = candles.iloc[idx]
    now = datetime.now(timezone.utc)

    # Only alert on fresh candles (closed within last 20 minutes)
    candle_time = c.name.to_pydatetime()
    if now - candle_time > timedelta(minutes=20):
        return None

    # Skip if already alerted on this candle
    candle_key = (symbol, candle_time)
    if candle_key in _alerted_candles:
        return None

    o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
    candle_range = h - l
    if candle_range <= 0:
        return None

    is_bullish = cl > o
    is_bearish = cl < o

    if not is_bullish and not is_bearish:
        return None  # doji

    # No open-side wick (bullish: open == low, bearish: open == high)
    # Tolerance: 1 point (0.1 pip) — essentially zero wick
    pip = 0.001 if "JPY" in symbol.upper().replace("/", "") else 0.00001
    wick_tolerance = pip

    if is_bullish:
        open_wick = abs(l - o)
    else:
        open_wick = abs(h - o)

    if open_wick > wick_tolerance:
        logger.debug(
            "Nova @ %s rejected: open-side wick %.5f",
            c.name, open_wick,
        )
        return None

    # --- All checks passed ---
    _alerted_candles.add(candle_key)

    direction = "BUY" if is_bullish else "SELL"
    logger.info(
        "%s NOVA @ %s O=%.5f H=%.5f L=%.5f C=%.5f",
        direction, c.name, o, h, l, cl,
    )

    return {
        "direction": direction,
        "entry_price": o,
        "candle_time": c.name,
        "signal_idx": idx,
        "open": o,
        "high": h,
        "low": l,
        "close": cl,
    }


# ---------------------------------------------------------------------------
# Scan all symbols
# ---------------------------------------------------------------------------

def scan_all_symbols(
    symbols: list[str],
) -> list[dict[str, Any]]:
    """Scan all symbols and return a list of nova candle signals."""
    # Purge stale entries from dedup set (older than 30 minutes)
    now = datetime.now(timezone.utc)
    _alerted_candles.difference_update(
        {(s, t) for s, t in _alerted_candles if now - t > timedelta(minutes=30)}
    )

    signals = []
    delay = 2  # seconds between requests

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(delay)
        candles = get_candles(symbol)
        if candles is None:
            continue

        result = find_nova_candle(candles, symbol)
        if result is not None:
            result["symbol"] = symbol
            result.update(calculate_trade_params(result, candles, result["signal_idx"]))
            signals.append(result)

    return signals


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def _to_signal(raw: dict[str, Any]) -> Signal:
    """Map a raw signal dict to the shared Signal dataclass."""
    return Signal(
        strategy="nova-candle",
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
            "open": raw["open"],
            "high": raw["high"],
            "low": raw["low"],
            "close": raw["close"],
            "bos_candle_time": raw.get("bos_candle_time"),
            "bos_swing_price": raw.get("bos_swing_price"),
        },
    )


def scan() -> list[Signal]:
    """Strategy plugin entry point. Called by the runner every 15 minutes.

    Reads NOVA_CANDLE_PAIRS env var (comma-separated) or falls back to
    the 7 major pairs.
    """
    symbols = [
        p.strip()
        for p in os.getenv("NOVA_CANDLE_PAIRS", DEFAULT_PAIRS).split(",")
        if p.strip()
    ]
    raw_signals = scan_all_symbols(symbols)
    return [_to_signal(s) for s in raw_signals]
