"""
api/services/ict_classifiers.py
---------------------------------
Time-based ICT session and killzone classifiers.

All functions take a datetime stored in ET (NY time — logged verbatim by trader)
and return a string bucket label. No timezone conversion required.

Session and killzone ranges apply to both MNQ (Micro E-mini Nasdaq) and
MES (Micro E-mini S&P 500) — both trade on CME Globex with identical hours.
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


# NY phases for the time-of-day edge analysis (finer than the coarse AM/lunch/PM split)
_NY_PHASE_RANGES: list[tuple[str, int, int]] = [
    ("pre_open",      8 * 60 + 30,  9 * 60 + 30),
    ("judas",         9 * 60 + 30,  9 * 60 + 45),
    ("post_judas",    9 * 60 + 45,  10 * 60),
    ("ny_open",       10 * 60,      10 * 60 + 30),
    ("late_session",  10 * 60 + 30, 11 * 60),
    ("after_session", 11 * 60,      16 * 60),
]

ALL_NY_PHASES: list[str] = [label for label, _, _ in _NY_PHASE_RANGES] + ["other"]

# ICT macro windows: the 20 minutes spanning xx:50 to (xx+1):10 (ET)
_MACRO_STARTS_MIN: list[int] = [
    8 * 60 + 50, 9 * 60 + 50, 10 * 60 + 50, 11 * 60 + 50,
    13 * 60 + 50, 14 * 60 + 50, 15 * 60 + 50,
]
_MACRO_LENGTH_MIN = 20
_SLICE_MINUTES = 15
_SLICE_FIRST_MIN = 8 * 60 + 30
_SLICE_LAST_MIN = 16 * 60


def _minutes(open_time: datetime) -> int:
    return open_time.hour * 60 + open_time.minute


def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def all_time_slices() -> list[str]:
    """Labels of every 15-minute slice between 08:30 and 16:00 ET, in order."""
    return [_clock(m) for m in range(_SLICE_FIRST_MIN, _SLICE_LAST_MIN, _SLICE_MINUTES)]


def all_macro_labels() -> list[str]:
    """Labels of every ICT macro window, in time order."""
    return [f"{_clock(s)}-{_clock(s + _MACRO_LENGTH_MIN)}" for s in _MACRO_STARTS_MIN]


def classify_time_slice(open_time: datetime) -> str:
    """Map open_time (ET) to its 15-minute slice label (e.g. '09:45'), else 'other'."""
    minutes = _minutes(open_time)
    if not _SLICE_FIRST_MIN <= minutes < _SLICE_LAST_MIN:
        return "other"
    offset = (minutes - _SLICE_FIRST_MIN) // _SLICE_MINUTES * _SLICE_MINUTES
    return _clock(_SLICE_FIRST_MIN + offset)


def classify_ny_phase(open_time: datetime) -> str:
    """Map open_time (ET) to a NY phase: pre_open / judas / post_judas / ... / other."""
    minutes = _minutes(open_time)
    for label, start, end in _NY_PHASE_RANGES:
        if start <= minutes < end:
            return label
    return "other"


def classify_macro(open_time: datetime) -> str:
    """Map open_time (ET) to its ICT macro window label, or 'outside'."""
    minutes = _minutes(open_time)
    for start in _MACRO_STARTS_MIN:
        if start <= minutes < start + _MACRO_LENGTH_MIN:
            return f"{_clock(start)}-{_clock(start + _MACRO_LENGTH_MIN)}"
    return "outside"


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


__all__ = [
    "ALL_MNQ_SESSIONS", "ALL_NY_PHASES", "KILLZONE_BUCKETS", "all_macro_labels",
    "all_time_slices", "classify_killzone", "classify_macro", "classify_mnq_session",
    "classify_ny_phase", "classify_time_slice",
]
