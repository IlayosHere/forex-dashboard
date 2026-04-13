"""
analytics/params/temporal.py
----------------------------
Time-based signal parameters: session label and day of week.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.registry import register
from analytics.types import Session

logger = logging.getLogger(__name__)

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
    hour: int = signal.candle_time.hour
    for start, end, session in _SESSION_RANGES:
        if start <= hour < end:
            return session.value
    return Session.CLOSE.value  # pragma: no cover — unreachable


@register("day_of_week", dtype="int")
def day_of_week(signal: Any, _candles: pd.DataFrame | None) -> int:
    """Return weekday index from signal.candle_time (0=Monday, 4=Friday)."""
    return signal.candle_time.weekday()
