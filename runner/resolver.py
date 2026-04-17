"""
runner/resolver.py
------------------
Signal resolution logic. Runs after each scan cycle to check if pending
signals have hit their TP or SL based on subsequent candles.

Resolution states:
  TP_HIT      — price reached take profit
  SL_HIT      — price reached stop loss
  NOT_FILLED  — limit-order never reached entry within fill window
  EXPIRED     — neither hit within MAX_RESOLUTION_CANDLES candles
  None        — still pending (not enough candles yet, skip)

Tie-breaking: if a candle touches both SL and TP, resolve as SL_HIT
(conservative — matches real-world fill behaviour on fast moves).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from tvDatafeed import Interval

from analytics.candle_cache import interval_for_strategy
from api.models import SignalModel
from runner.resolution_strategies import (
    MAX_RESOLUTION_CANDLES,
    NOVA_FILL_CANDLES as NOVA_FILL_CANDLES,  # re-exported for tests
    check_bar,
    check_fill,
    resolve_midpoint,
    resolve_nova,
    resolve_price,
)
from shared.market_data import get_candles

logger = logging.getLogger(__name__)


def _resolve_nova(signal: SignalModel, df: pd.DataFrame, start_idx: int) -> bool:
    """Test-compatible 3-arg wrapper around resolve_nova; passes last available bar as closed_end."""
    return resolve_nova(signal, df, start_idx, len(df) - 1)

_INTERVAL_SECONDS: dict[Interval, int] = {
    Interval.in_5_minute:  5 * 60,
    Interval.in_15_minute: 15 * 60,
}
_DEFAULT_INTERVAL_SECONDS: int = 15 * 60
_LIMIT_ORDER_STRATEGIES: frozenset[str] = frozenset({"nova-candle"})
_STANDARD_STRATEGIES: frozenset[str] = frozenset({"fvg-impulse", "fvg-impulse-5m"})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _bars_needed(signals: list[SignalModel], strategy: str) -> int:
    """Compute how many bars to request for a group of same-symbol, same-strategy signals."""
    interval = interval_for_strategy(strategy)
    bar_seconds = _INTERVAL_SECONDS.get(interval, _DEFAULT_INTERVAL_SECONDS)
    now = datetime.now(timezone.utc)
    oldest = min(s.candle_time for s in signals)
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - oldest).total_seconds()
    candles_since_oldest = math.ceil(elapsed_seconds / bar_seconds)
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


_INTERVAL_MINUTES: dict[Interval, int] = {
    Interval.in_5_minute:  5,
    Interval.in_15_minute: 15,
}
_DEFAULT_INTERVAL_MINUTES: int = 15


def _last_closed_idx(df: pd.DataFrame, strategy: str) -> int:
    """Return the index of the last fully-closed candle for the strategy's timeframe.

    The currently-forming candle has partially-committed OHLC data from the
    live feed. Scanning it can produce false fills or false TP/SL hits based
    on intrabar ticks that are later corrected. Always cap resolution scans
    to this index.
    """
    interval = interval_for_strategy(strategy)
    bar_minutes = _INTERVAL_MINUTES.get(interval, _DEFAULT_INTERVAL_MINUTES)
    now = datetime.now(timezone.utc)
    current_boundary = now.replace(
        minute=(now.minute // bar_minutes) * bar_minutes, second=0, microsecond=0
    )
    for i in range(len(df) - 1, -1, -1):
        ts = df.index[i]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts < current_boundary:
            return i
    logger.warning(
        "_last_closed_idx: no closed bars found for strategy='%s' — defaulting to idx=0. "
        "Check if feed is returning future-dated candles.",
        strategy,
    )
    return 0


def _resolve_standard(
    signal: SignalModel,
    df: pd.DataFrame,
    start_idx: int,
    last_closed: int,
) -> bool:
    """Resolve a market-order signal by scanning for TP/SL hits.

    Returns True if resolved, False if more candles are needed.
    """
    last_idx = min(start_idx + MAX_RESOLUTION_CANDLES, last_closed)
    for i in range(start_idx + 1, last_idx + 1):
        row = df.iloc[i]
        label = check_bar(signal, float(row["high"]), float(row["low"]))
        if label is not None:
            signal.resolution = label
            signal.resolved_at = df.index[i].to_pydatetime().replace(tzinfo=timezone.utc)
            signal.resolved_price = resolve_price(signal, label, float(row["close"]))
            signal.resolution_candles = i - start_idx
            # Both fvg-impulse and fvg-impulse-5m store sl_midpoint in metadata
            # and benefit from midpoint resolution tracking.
            if signal.strategy in {"fvg-impulse", "fvg-impulse-5m"}:
                resolve_midpoint(signal, df, start_idx, last_closed)
            return True

    if (last_idx - start_idx) >= MAX_RESOLUTION_CANDLES:
        last_row = df.iloc[last_idx]
        signal.resolution = "EXPIRED"
        signal.resolved_at = df.index[last_idx].to_pydatetime().replace(tzinfo=timezone.utc)
        signal.resolved_price = float(last_row["close"])
        signal.resolution_candles = last_idx - start_idx
        # Both fvg-impulse and fvg-impulse-5m store sl_midpoint in metadata
        # and benefit from midpoint resolution tracking.
        if signal.strategy in {"fvg-impulse", "fvg-impulse-5m"}:
            resolve_midpoint(signal, df, start_idx, last_closed)
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

    last_closed = _last_closed_idx(df, signal.strategy)
    if signal.strategy in _LIMIT_ORDER_STRATEGIES:
        return resolve_nova(signal, df, start_idx, last_closed)
    if signal.strategy in _STANDARD_STRATEGIES:
        return _resolve_standard(signal, df, start_idx, last_closed)
    logger.warning(
        "_resolve_signal: unknown strategy '%s' for signal %s — skipping resolution, add to _STANDARD_STRATEGIES or _LIMIT_ORDER_STRATEGIES",
        signal.strategy, signal.id,
    )
    return False


def _update_pending_midpoints(
    signals: list[SignalModel],
    df: pd.DataFrame,
    strategy: str,
) -> int:
    """Update midpoint resolution on still-pending FVG Impulse signals.

    Returns the number of signals whose metadata was updated.
    """
    last_closed = _last_closed_idx(df, strategy)
    updated = 0
    for signal in signals:
        if signal.resolution is not None or signal.strategy not in {"fvg-impulse", "fvg-impulse-5m"}:
            continue
        start_idx = _signal_candle_idx(df, signal.candle_time)
        if start_idx is None:
            continue
        meta_before = dict(signal.signal_metadata or {})
        resolve_midpoint(signal, df, start_idx, last_closed)
        if signal.signal_metadata != meta_before:
            updated += 1
    return updated


def _resolve_symbol_strategy_group(
    symbol: str,
    strategy: str,
    signals: list[SignalModel],
    db: Session,
) -> int:
    """Fetch candles and resolve all signals for one (symbol, strategy) group.

    Fetches at the strategy's native timeframe so M5 signals are resolved
    against M5 candles and M15 signals against M15 candles.

    Returns the count of signals resolved this call.
    """
    interval = interval_for_strategy(strategy)
    count = _bars_needed(signals, strategy)
    df = get_candles(symbol, interval, count=count)
    if df is None:
        logger.warning(
            "Resolution: no candle data for %s @ %s — skipping %d signal(s)",
            symbol, strategy, len(signals),
        )
        return 0

    resolved = sum(1 for sig in signals if _resolve_signal(sig, df))
    if resolved:
        db.commit()

    if _update_pending_midpoints(signals, df, strategy):
        db.commit()

    return resolved


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_pending_signals(db: Session) -> int:
    """Check all unresolved signals against recent candles and persist results.

    Signals are grouped by (symbol, strategy) so that each group fetches the
    correct timeframe for its strategy — M5 for fvg-impulse-5m, M15 for
    fvg-impulse and nova-candle. Commits once per group to avoid long transactions.

    Returns the total count of signals resolved this cycle.
    """
    pending: list[SignalModel] = list(
        db.scalars(
            select(SignalModel).where(SignalModel.resolution.is_(None))
        ).all()
    )
    if not pending:
        return 0

    by_symbol_strategy: dict[tuple[str, str], list[SignalModel]] = {}
    for sig in pending:
        by_symbol_strategy.setdefault((sig.symbol, sig.strategy), []).append(sig)

    return sum(
        _resolve_symbol_strategy_group(symbol, strategy, signals, db)
        for (symbol, strategy), signals in by_symbol_strategy.items()
    )
