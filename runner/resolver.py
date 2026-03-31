"""
runner/resolver.py
------------------
Signal resolution logic. Runs after each scan cycle to check if pending
signals have hit their TP or SL based on subsequent M15 candles.

Resolution states:
  TP_HIT  — price reached take profit (BUY: high >= tp; SELL: low <= tp)
  SL_HIT  — price reached stop loss  (BUY: low <= sl;  SELL: high >= sl)
  EXPIRED — neither hit within MAX_RESOLUTION_CANDLES candles
  None    — still pending (not enough candles yet, skip)

Tie-breaking: if a candle touches both SL and TP, resolve as SL_HIT
(conservative — matches real-world fill behaviour on fast moves).
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import SignalModel
from strategies.fvg_impulse.data import get_candles

logger = logging.getLogger(__name__)

MAX_RESOLUTION_CANDLES: int = int(os.getenv("SIGNAL_EXPIRY_CANDLES", "96"))
NOVA_FILL_CANDLES: int = 10
_M15_SECONDS: int = 15 * 60

# Strategies that use a limit-order entry (require fill check before TP/SL scan)
_LIMIT_ORDER_STRATEGIES: frozenset[str] = frozenset({"nova-candle"})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _bars_needed(signals: list[SignalModel]) -> int:
    """Compute how many M15 bars to request for a group of same-symbol signals."""
    now = datetime.now(timezone.utc)
    oldest = min(s.candle_time for s in signals)
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - oldest).total_seconds()
    candles_since_oldest = math.ceil(elapsed_seconds / _M15_SECONDS)
    needed = candles_since_oldest + MAX_RESOLUTION_CANDLES + 10
    return min(needed, 500)


def _signal_candle_idx(df: pd.DataFrame, candle_time: datetime) -> int | None:
    """Return the first DataFrame row index where df.index >= candle_time, or None."""
    if candle_time.tzinfo is None:
        candle_time = candle_time.replace(tzinfo=timezone.utc)
    matches = df.index >= candle_time
    if not matches.any():
        return None
    return int(matches.argmax())


def _last_closed_idx(df: pd.DataFrame) -> int:
    """Return the index of the last fully-closed M15 candle.

    The currently-forming candle has partially-committed OHLC data from the
    live feed.  Scanning it can produce false fills or false TP/SL hits based
    on intrabar ticks that are later corrected.  Always cap resolution scans
    to this index.
    """
    now = datetime.now(timezone.utc)
    current_boundary = now.replace(
        minute=(now.minute // 15) * 15, second=0, microsecond=0
    )
    for i in range(len(df) - 1, -1, -1):
        ts = df.index[i]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < current_boundary:
            return i
    return 0


def _check_bar(
    signal: SignalModel,
    bar_high: float,
    bar_low: float,
) -> str | None:
    """Return resolution label if the bar resolves the signal, else None."""
    if signal.direction == "BUY":
        sl_hit = bar_low <= signal.sl
        tp_hit = bar_high >= signal.tp
    else:
        sl_hit = bar_high >= signal.sl
        tp_hit = bar_low <= signal.tp

    if sl_hit:      # tie-break: SL wins
        return "SL_HIT"
    if tp_hit:
        return "TP_HIT"
    return None


def _resolve_price(signal: SignalModel, label: str, bar_close: float) -> float:
    """Return the canonical resolved_price for each resolution label."""
    if label == "TP_HIT":
        return signal.tp
    if label == "SL_HIT":
        return signal.sl
    return bar_close  # EXPIRED


def _check_fill(signal: SignalModel, bar_high: float, bar_low: float) -> bool:
    """Return True if the bar's range reached the limit entry price."""
    if signal.direction == "BUY":
        return bar_low <= signal.entry
    return bar_high >= signal.entry


def _find_fill_bar(
    df: pd.DataFrame,
    start_idx: int,
    fill_end_idx: int,
    signal: SignalModel,
) -> int | None:
    """Scan Phase 1 fill window and return the fill bar index, or None if not filled."""
    for i in range(start_idx + 1, fill_end_idx + 1):
        row = df.iloc[i]
        if _check_fill(signal, float(row["high"]), float(row["low"])):
            return i
    return None


def _resolve_nova(signal: SignalModel, df: pd.DataFrame, start_idx: int) -> bool:
    """Two-phase resolution for limit-order strategies (e.g. Nova Candle).

    Phase 1 — fill check (NOVA_FILL_CANDLES bars):
        Walk candles after the signal looking for price to reach entry.
        If not filled within the window → NOT_FILLED.
        If not enough candles yet → return False (try again next cycle).

    Phase 2 — TP/SL scan (up to MAX_RESOLUTION_CANDLES from fill bar):
        Starting from the fill bar (inclusive, since the same bar could also
        hit TP or SL), scan forward. Tie-break: SL wins.
        If neither hit within the window → EXPIRED.

    resolution_candles is always counted from start_idx so it is comparable
    across both strategies.

    Both phases are capped at _last_closed_idx to exclude the currently-forming
    candle whose live OHLC may contain transient tick data.
    """
    closed_end = _last_closed_idx(df)
    fill_end_idx = min(start_idx + NOVA_FILL_CANDLES, closed_end)
    fill_idx = _find_fill_bar(df, start_idx, fill_end_idx, signal)

    if fill_idx is None:
        # Declare NOT_FILLED only once the full fill window has closed
        if (fill_end_idx - start_idx) < NOVA_FILL_CANDLES:
            return False
        last_row = df.iloc[fill_end_idx]
        signal.resolution = "NOT_FILLED"
        signal.resolved_at = df.index[fill_end_idx].to_pydatetime().replace(tzinfo=timezone.utc)
        signal.resolved_price = float(last_row["close"])
        signal.resolution_candles = fill_end_idx - start_idx
        return True

    # Phase 2: scan for TP/SL starting at the fill bar
    tp_sl_end_idx = min(fill_idx + MAX_RESOLUTION_CANDLES, closed_end)

    for i in range(fill_idx, tp_sl_end_idx + 1):
        row = df.iloc[i]
        label = _check_bar(signal, float(row["high"]), float(row["low"]))
        if label is not None:
            signal.resolution = label
            signal.resolved_at = df.index[i].to_pydatetime().replace(tzinfo=timezone.utc)
            signal.resolved_price = _resolve_price(signal, label, float(row["close"]))
            signal.resolution_candles = i - start_idx
            return True

    elapsed = tp_sl_end_idx - fill_idx
    if elapsed >= MAX_RESOLUTION_CANDLES:
        last_row = df.iloc[tp_sl_end_idx]
        signal.resolution = "EXPIRED"
        signal.resolved_at = df.index[tp_sl_end_idx].to_pydatetime().replace(tzinfo=timezone.utc)
        signal.resolved_price = float(last_row["close"])
        signal.resolution_candles = tp_sl_end_idx - start_idx
        return True

    return False


def _resolve_signal(signal: SignalModel, df: pd.DataFrame) -> bool:
    """Attempt to resolve a single signal against the given DataFrame.

    Returns True if the signal was resolved (caller must commit), False if
    there are not yet enough candles to make a determination.
    """
    start_idx = _signal_candle_idx(df, signal.candle_time)
    if start_idx is None:
        logger.debug("Signal %s candle not found in DataFrame — skipping", signal.id)
        return False

    if signal.strategy in _LIMIT_ORDER_STRATEGIES:
        return _resolve_nova(signal, df, start_idx)

    last_idx = min(start_idx + MAX_RESOLUTION_CANDLES, _last_closed_idx(df))

    for i in range(start_idx + 1, last_idx + 1):
        row = df.iloc[i]
        label = _check_bar(signal, float(row["high"]), float(row["low"]))
        if label is not None:
            signal.resolution = label
            signal.resolved_at = df.index[i].to_pydatetime().replace(tzinfo=timezone.utc)
            signal.resolved_price = _resolve_price(signal, label, float(row["close"]))
            signal.resolution_candles = i - start_idx
            return True

    elapsed = last_idx - start_idx
    if elapsed >= MAX_RESOLUTION_CANDLES:
        last_row = df.iloc[last_idx]
        signal.resolution = "EXPIRED"
        signal.resolved_at = df.index[last_idx].to_pydatetime().replace(tzinfo=timezone.utc)
        signal.resolved_price = float(last_row["close"])
        signal.resolution_candles = elapsed
        return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_pending_signals(db: Session) -> int:
    """Check all unresolved signals against recent M15 candles and persist results.

    Signals are grouped by symbol so that only one tvDatafeed call is made per
    symbol per cycle. Commits once per symbol group to avoid long transactions.

    Returns the total count of signals resolved this cycle.
    """
    pending: list[SignalModel] = list(
        db.scalars(
            select(SignalModel).where(SignalModel.resolution.is_(None))
        ).all()
    )
    if not pending:
        return 0

    by_symbol: dict[str, list[SignalModel]] = {}
    for sig in pending:
        by_symbol.setdefault(sig.symbol, []).append(sig)

    total_resolved = 0

    for symbol, signals in by_symbol.items():
        count = _bars_needed(signals)
        df = get_candles(symbol, count=count)
        if df is None:
            logger.warning("Resolution: no candle data for %s — skipping %d signal(s)", symbol, len(signals))
            continue

        resolved_this_symbol = 0
        for signal in signals:
            if _resolve_signal(signal, df):
                resolved_this_symbol += 1
                logger.debug(
                    "Resolved %s %s %s → %s after %s candle(s)",
                    signal.strategy, signal.symbol, signal.direction,
                    signal.resolution, signal.resolution_candles,
                )

        if resolved_this_symbol:
            db.commit()
            total_resolved += resolved_this_symbol

    return total_resolved
