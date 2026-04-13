"""
runner/resolution_strategies.py
---------------------------------
Strategy-specific resolution logic for signal resolution.

Contains two-phase (limit-order) resolution for Nova Candle strategy and
midpoint resolution for FVG Impulse strategy. Called by resolver.py.
"""
from __future__ import annotations

import logging
import os
from datetime import timezone

import pandas as pd

from api.models import SignalModel

logger = logging.getLogger(__name__)

MAX_RESOLUTION_CANDLES: int = int(os.getenv("SIGNAL_EXPIRY_CANDLES", "96"))
NOVA_FILL_CANDLES: int = int(os.getenv("NOVA_FILL_CANDLES", "10"))


def check_fill(signal: SignalModel, bar_high: float, bar_low: float) -> bool:
    """Return True if the bar's range reached the limit entry price."""
    if signal.direction == "BUY":
        return bar_low <= signal.entry
    return bar_high >= signal.entry


def check_bar(signal: SignalModel, bar_high: float, bar_low: float) -> str | None:
    """Return resolution label if the bar resolves the signal, else None."""
    if signal.direction == "BUY":
        sl_hit = bar_low <= signal.sl
        tp_hit = bar_high >= signal.tp
    else:
        sl_hit = bar_high >= signal.sl
        tp_hit = bar_low <= signal.tp

    if sl_hit:  # tie-break: SL wins
        return "SL_HIT"
    if tp_hit:
        return "TP_HIT"
    return None


def resolve_price(signal: SignalModel, label: str, bar_close: float) -> float:
    """Return the canonical resolved_price for each resolution label."""
    if label == "TP_HIT":
        return signal.tp
    if label == "SL_HIT":
        return signal.sl
    return bar_close  # EXPIRED


def _find_fill_bar(
    df: pd.DataFrame,
    start_idx: int,
    fill_end_idx: int,
    signal: SignalModel,
) -> int | None:
    """Scan Phase 1 fill window and return the fill bar index, or None if not filled."""
    for i in range(start_idx + 1, fill_end_idx + 1):
        row = df.iloc[i]
        if check_fill(signal, float(row["high"]), float(row["low"])):
            return i
    return None


def _resolve_nova_phase2(
    signal: SignalModel,
    df: pd.DataFrame,
    fill_idx: int,
    start_idx: int,
    closed_end: int,
) -> bool:
    """Scan for TP/SL starting from the fill bar. Returns True if resolved."""
    tp_sl_end_idx = min(fill_idx + MAX_RESOLUTION_CANDLES, closed_end)
    for i in range(fill_idx, tp_sl_end_idx + 1):
        row = df.iloc[i]
        label = check_bar(signal, float(row["high"]), float(row["low"]))
        if label is not None:
            signal.resolution = label
            signal.resolved_at = df.index[i].to_pydatetime().replace(tzinfo=timezone.utc)
            signal.resolved_price = resolve_price(signal, label, float(row["close"]))
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


def resolve_nova(signal: SignalModel, df: pd.DataFrame, start_idx: int, closed_end: int) -> bool:
    """Two-phase resolution for limit-order strategies (e.g. Nova Candle).

    Phase 1 — fill check (NOVA_FILL_CANDLES bars):
        Walk candles after the signal looking for price to reach entry.
        If not filled within the window → NOT_FILLED.
        If not enough candles yet → return False (try again next cycle).

    Phase 2 — TP/SL scan (up to MAX_RESOLUTION_CANDLES from fill bar):
        Starting from the fill bar, scan forward. Tie-break: SL wins.
        If neither hit within the window → EXPIRED.

    Returns True if the signal was resolved, False if more candles needed.
    """
    fill_end_idx = min(start_idx + NOVA_FILL_CANDLES, closed_end)
    fill_idx = _find_fill_bar(df, start_idx, fill_end_idx, signal)

    if fill_idx is None:
        if (fill_end_idx - start_idx) < NOVA_FILL_CANDLES:
            return False
        last_row = df.iloc[fill_end_idx]
        signal.resolution = "NOT_FILLED"
        signal.resolved_at = df.index[fill_end_idx].to_pydatetime().replace(tzinfo=timezone.utc)
        signal.resolved_price = float(last_row["close"])
        signal.resolution_candles = fill_end_idx - start_idx
        return True

    return _resolve_nova_phase2(signal, df, fill_idx, start_idx, closed_end)


def resolve_midpoint(
    signal: SignalModel,
    df: pd.DataFrame,
    start_idx: int,
    last_closed: int,
) -> None:
    """Write resolution_midpoint to signal metadata using the midpoint SL price.

    Runs independently of the far-edge resolution so that signals still pending
    on far-edge can accumulate midpoint data on each cycle. Idempotent: exits
    immediately if resolution_midpoint already present in metadata.

    Writes nothing if the candle window is not yet large enough.
    """
    meta = signal.signal_metadata or {}
    sl_midpoint: float | None = meta.get("sl_midpoint")
    if sl_midpoint is None:
        logger.warning(
            "resolve_midpoint: signal %s has no sl_midpoint in metadata, skipping",
            signal.id,
        )
        return
    if "resolution_midpoint" in meta:
        return

    tp_midpoint: float = 2 * signal.entry - sl_midpoint
    end_idx = min(start_idx + MAX_RESOLUTION_CANDLES, last_closed)

    for i in range(start_idx + 1, end_idx + 1):
        row = df.iloc[i]
        bar_high, bar_low = float(row["high"]), float(row["low"])
        if signal.direction == "BUY":
            sl_hit, tp_hit = bar_low <= sl_midpoint, bar_high >= tp_midpoint
        else:
            sl_hit, tp_hit = bar_high >= sl_midpoint, bar_low <= tp_midpoint

        label = "SL_HIT" if sl_hit else ("TP_HIT" if tp_hit else None)
        if label is not None:
            signal.signal_metadata = {
                **meta,
                "resolution_midpoint": label,
                "resolution_midpoint_candles": i - start_idx,
            }
            return

    if (end_idx - start_idx) >= MAX_RESOLUTION_CANDLES:
        signal.signal_metadata = {
            **meta,
            "resolution_midpoint": "EXPIRED",
            "resolution_midpoint_candles": end_idx - start_idx,
        }
