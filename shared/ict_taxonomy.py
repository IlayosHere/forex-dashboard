"""ICT trade taxonomy constants for MNQ journaling.

Single source of truth for all ICT-specific enum values.
Imported by API schemas and used to generate frontend select options.
"""
from __future__ import annotations

from typing import Final

# Setup types
SETUP_TYPES: Final[list[str]] = [
    "liquidity_sweep",
    "unmitigated_fvg",
    "continuation",
    "other",
]

# Setup detail values per setup type
# For liquidity_sweep: the liquidity level that was swept (entry reason)
LIQUIDITY_SWEEP_DETAILS: Final[list[str]] = [
    "london_high",
    "london_low",
    "asia_high",
    "asia_low",
    "data_high",
    "data_low",
    "1m_high",
    "1m_low",
    "5m_high",
    "5m_low",
    "15m_high",
    "15m_low",
    "1h_high",
    "1h_low",
    "4h_high",
    "4h_low",
    "1d_high",
    "1d_low",
    "gap_fill",
    "other",
]

# For unmitigated_fvg: the timeframe of the FVG
UNMITIGATED_FVG_DETAILS: Final[list[str]] = [
    "15m",
    "30m",
    "1h",
    "4h",
    "other",
]

# For continuation: the timeframe the continuation FVG formed on
CONTINUATION_DETAILS: Final[list[str]] = [
    "3m",
    "5m",
    "15m",
    "other",
]

# TP targets — what price level / FVG is being targeted
TP_TARGETS: Final[list[str]] = [
    "london_high",
    "london_low",
    "asia_high",
    "asia_low",
    "data_high",
    "data_low",
    "1m_high",
    "1m_low",
    "5m_high",
    "5m_low",
    "15m_high",
    "15m_low",
    "1h_high",
    "1h_low",
    "4h_high",
    "4h_low",
    "1d_high",
    "1d_low",
    "unmitigated_5m_fvg",
    "unmitigated_15m_fvg",
    "unmitigated_30m_fvg",
    "unmitigated_1h_fvg",
    "unmitigated_4h_fvg",
    "other",
]

# Mapping from setup_type -> valid detail values (used for cross-validation)
SETUP_DETAIL_MAP: Final[dict[str, list[str]]] = {
    "liquidity_sweep": LIQUIDITY_SWEEP_DETAILS,
    "unmitigated_fvg": UNMITIGATED_FVG_DETAILS,
    "continuation": CONTINUATION_DETAILS,
    "other": [],  # no detail required for "other"
}

# HTF bias alignment
HTF_BIAS_VALUES: Final[list[str]] = [
    "aligned",
    "counter",
    "neutral",
]

# Entry model
ENTRY_MODELS: Final[list[str]] = [
    "silver_bullet",
    "cisd",
    "bms",
    "ote",
    "turtle_soup",
    "other",
]

# Premium / discount / equilibrium at entry
PD_ARRAY_VALUES: Final[list[str]] = [
    "premium",
    "discount",
    "equilibrium",
]

# Killzone windows (derived from open_time — not a logged field)
# Defined here as the canonical bucket labels used by the stats service.
KILLZONE_BUCKETS: Final[list[str]] = [
    "london",
    "ny_am_kz",
    "silver_bullet_am",
    "lunch",
    "ny_pm_kz",
    "silver_bullet_pm",
    "close",
    "other",
]

# IFVG confirmation timeframe
IFVG_TIMEFRAMES: Final[list[str]] = [
    "1m",
    "2m",
    "3m",
    "4m",
    "5m",
    "6m",
    "7m",
    "8m",
    "9m",
    "10m",
    "15m",
    "other",
]
