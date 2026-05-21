"""QT trade taxonomy constants for qt-mnq journaling.

Single source of truth for all QT-specific enum values.
Imported by API schemas and used to generate frontend select options.
"""
from __future__ import annotations

from typing import Final

QT_QUARTERS: Final[list[str]] = [
    "asia_q1", "asia_q2", "asia_q3", "asia_q4",
    "london_q1", "london_q2", "london_q3", "london_q4",
    "ny_am_q1", "ny_am_q2", "ny_am_q3", "ny_am_q4",
    "ny_pm_q1", "ny_pm_q2", "ny_pm_q3", "ny_pm_q4",
]

QT_FVG_TYPES: Final[list[str]] = ["standard", "inverse"]

QT_ENTRY_TYPES: Final[list[str]] = ["limit_fvg_edge", "market_mss"]

QT_TP_TARGETS: Final[list[str]] = [
    "opposing_session_high", "opposing_session_low",
    "prior_q3_fvg", "prior_q1_fvg",
    "lqp_250", "daily_high", "daily_low",
    "unmitigated_15m_fvg", "unmitigated_1h_fvg", "unmitigated_4h_fvg",
    "other",
]
