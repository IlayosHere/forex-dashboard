"""
api/services/ict_classifiers.py
---------------------------------
Time-based ICT session and killzone classifiers.

All functions take a datetime stored in ET (NY time — logged verbatim by trader)
and return a string bucket label. No timezone conversion required.
"""
from __future__ import annotations

from datetime import datetime

from shared.ict_taxonomy import KILLZONE_BUCKETS

# Session boundaries: (label, start_minutes_et_inclusive, end_minutes_et_exclusive)
_MNQ_SESSION_RANGES: list[tuple[str, int, int]] = [
    ("am",    9 * 60 + 30,  11 * 60 + 30),
    ("lunch", 11 * 60 + 30, 13 * 60),
    ("pm",    13 * 60,      16 * 60),
]

ALL_MNQ_SESSIONS: list[str] = ["am", "lunch", "pm", "other"]

# Killzone boundaries: (label, start_minutes_et_inclusive, end_minutes_et_exclusive)
_KILLZONE_RANGES: list[tuple[str, int, int]] = [
    ("london",           2 * 60,       5 * 60),
    ("ny_am_kz",         8 * 60 + 30,  10 * 60),
    ("silver_bullet_am", 10 * 60,      11 * 60),
    ("lunch",            11 * 60,      13 * 60 + 30),
    ("ny_pm_kz",         13 * 60 + 30, 14 * 60),
    ("silver_bullet_pm", 14 * 60,      15 * 60),
    ("close",            15 * 60,      16 * 60),
]


def classify_mnq_session(open_time: datetime) -> str:
    """Map open_time (ET) to a coarse MNQ session: am / lunch / pm / other."""
    et_minutes = open_time.hour * 60 + open_time.minute
    for label, start, end in _MNQ_SESSION_RANGES:
        if start <= et_minutes < end:
            return label
    return "other"


def classify_killzone(open_time: datetime) -> str:
    """Map open_time (ET) to an ICT killzone bucket label."""
    et_minutes = open_time.hour * 60 + open_time.minute
    for label, start, end in _KILLZONE_RANGES:
        if start <= et_minutes < end:
            return label
    return "other"


__all__ = ["ALL_MNQ_SESSIONS", "KILLZONE_BUCKETS", "classify_killzone", "classify_mnq_session"]
