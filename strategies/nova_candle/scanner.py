"""
scanner.py - Nova (wickless) momentum candle scanner using TradingView data.

Fetches 15M candles for each symbol via tvDatafeed (TradingView) and checks
for nova candles: no wick on the open side (open == low for bullish,
open == high for bearish).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from tvDatafeed import TvDatafeed, Interval

logger = logging.getLogger(__name__)

_tv: TvDatafeed | None = None

# Already-alerted candles: set of (symbol, candle_time) to prevent duplicate alerts
_alerted_candles: set = set()


def _get_tv() -> TvDatafeed:
    """Get or create the TvDatafeed connection (lazy singleton)."""
    global _tv
    if _tv is None:
        _tv = TvDatafeed()
        _tv._TvDatafeed__ws_timeout = 15
        logger.info("TvDatafeed connection established")
    return _tv


def _reset_tv() -> None:
    """Force reconnection on next call."""
    global _tv
    _tv = None
    logger.warning("TvDatafeed connection reset, will reconnect on next call")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_candles(symbol: str, count: int = 70) -> Optional[pd.DataFrame]:
    """Fetch M15 candles from TradingView. Returns DataFrame or None."""
    df = None
    for attempt in range(2):
        try:
            tv = _get_tv()
            df = tv.get_hist(
                symbol=symbol,
                exchange="PEPPERSTONE",
                interval=Interval.in_15_minute,
                n_bars=count,
            )
        except Exception as exc:
            logger.error("TradingView request failed for %s (attempt %d): %s",
                         symbol, attempt + 1, exc)

        if df is not None and not df.empty:
            break

        # Retry once with a fresh connection
        if attempt == 0:
            _reset_tv()
            time.sleep(2)

    if df is None or df.empty:
        logger.error("No data returned for %s", symbol)
        return None

    df = df[["open", "high", "low", "close"]].copy()
    # tvDatafeed uses datetime.fromtimestamp() which returns local time.
    # Convert from local timezone to UTC for consistent comparisons.
    local_tz = datetime.now(timezone.utc).astimezone().tzinfo
    if df.index.tz is None:
        df.index = df.index.tz_localize(local_tz).tz_convert(timezone.utc)
    return df


# ---------------------------------------------------------------------------
# Nova (wickless momentum) candle detection
# ---------------------------------------------------------------------------

def _find_last_closed_index(candles: pd.DataFrame) -> Optional[int]:
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
) -> Optional[Dict[str, Any]]:
    """
    Inspect the last closed candle for a Nova (wickless momentum) pattern.

    Criteria:
    1. No open-side wick (open == low for bullish, open == high for bearish)
    2. Trend filter: close must be above EMA 50 for BUY, below for SELL

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
    # Tolerance: 2 pip (3rd decimal for JPY, 5th decimal for others)
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

    # Trend filter: price must be on the right side of EMA 50
    if len(candles) >= 50:
        ema50 = candles["close"].ewm(span=50, adjust=False).mean().iloc[idx]
        if is_bullish and cl < ema50:
            logger.debug("Nova @ %s rejected: BUY but close %.5f < EMA50 %.5f", c.name, cl, ema50)
            return None
        if is_bearish and cl > ema50:
            logger.debug("Nova @ %s rejected: SELL but close %.5f > EMA50 %.5f", c.name, cl, ema50)
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
        "open": o,
        "high": h,
        "low": l,
        "close": cl,
    }


# ---------------------------------------------------------------------------
# Scan all symbols
# ---------------------------------------------------------------------------

def scan_all_symbols(
    symbols: List[str],
) -> List[Dict[str, Any]]:
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
            signals.append(result)

    return signals
