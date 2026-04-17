"""
analytics/params/temporal.py
----------------------------
Time-based signal parameters: session label and day of week.
"""
from __future__ import annotations

import logging
from datetime import timezone
from typing import Any

import pandas as pd

from analytics.registry import register
from analytics.types import Session

logger = logging.getLogger(__name__)

# NOTE: These boundaries differ from _SESSIONS in api/services/trade_stats_extended.py.
# That module uses coarser buckets (asian 0-8, london 8-13, overlap 13-17, new_york 17-22)
# for trade-level journal aggregation. These finer-grained ranges are used for per-signal
# analytics classification and map to Session enum values in analytics/types.py.
# Neither is authoritative over the other — they serve different purposes.
# Reconcile both if a single session taxonomy is ever required project-wide.
# Hour-range boundaries (inclusive start, exclusive end)
_SESSION_RANGES: list[tuple[int, int, Session]] = [
    (0, 7, Session.ASIAN),
    (7, 12, Session.LONDON),
    (12, 16, Session.NY_OVERLAP),
    (16, 21, Session.NY_LATE),
    (21, 24, Session.CLOSE),
]


@register("session_label", dtype="str")
def session_label(signal: Any, _candles: pd.DataFrame | None) -> str:
    """Map the signal's candle_time UTC hour to a trading session name."""
    ct = signal.candle_time
    if ct.tzinfo is None:
        ct = ct.replace(tzinfo=timezone.utc)
    hour: int = ct.hour
    for start, end, session in _SESSION_RANGES:
        if start <= hour < end:
            return session.value
    return Session.CLOSE.value  # pragma: no cover — unreachable


@register("day_of_week", dtype="int")
def day_of_week(signal: Any, _candles: pd.DataFrame | None) -> int:
    """Return weekday index from signal.candle_time (0=Monday, 4=Friday)."""
    ct = signal.candle_time
    if ct.tzinfo is None:
        ct = ct.replace(tzinfo=timezone.utc)
    return int(ct.weekday())
