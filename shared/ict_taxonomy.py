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
    "2h",
    "4h",
    "1D",
    "1W",
    "1M",
    "other",
]

# For continuation: the timeframe the continuation FVG formed on
CONTINUATION_DETAILS: Final[list[str]] = [
    "3m",
    "5m",
    "15m",
    "other",
]

# TP targets — what price level / FVG is being targeted.
# Deliberately excludes raw low-timeframe candle highs/lows (the old 1m/5m/15m_high/low
# values) — those aren't real ICT draw-on-liquidity concepts, just noise. A swing high/low
# formed on a given timeframe now lives under ith/itl + TP_TARGET_DETAIL_MAP instead.
TP_TARGETS: Final[list[str]] = [
    "asia_high",
    "asia_low",
    "london_high",
    "london_low",
    "prev_session_high",   # previous NY session's high (session, not calendar day)
    "prev_session_low",
    "pdh",                  # previous day high
    "pdl",                  # previous day low
    "pwh",                  # previous week high
    "pwl",                  # previous week low
    "pmh",                  # previous month high
    "pml",                  # previous month low
    "ith",                  # intermediate term high (swing structure) — see TP_TARGET_DETAIL_MAP
    "itl",                  # intermediate term low (swing structure) — see TP_TARGET_DETAIL_MAP
    "nwog",                 # new week opening gap
    "ndog",                 # new day opening gap
    "unmitigated_fvg",      # see TP_TARGET_DETAIL_MAP for timeframe
    "data_release_high",    # wick from a scheduled release (CPI/PPI/NFP/FOMC) — see TP_TARGET_DETAIL_MAP
    "data_release_low",
    "ath",
    "other",
]

# Detail values valid per tp_target, for the values above that need a sub-selection.
# Any tp_target not listed here takes no detail (tp_target_detail must be None).
TP_TARGET_DETAIL_MAP: Final[dict[str, list[str]]] = {
    "ith": ["5m", "15m", "30m", "1h", "4h", "1D", "1W"],
    "itl": ["5m", "15m", "30m", "1h", "4h", "1D", "1W"],
    "unmitigated_fvg": ["5m", "15m", "30m", "1h", "2h", "4h", "1D", "1W", "1M"],
    "data_release_high": ["cpi", "ppi", "nfp", "fomc", "other"],
    "data_release_low": ["cpi", "ppi", "nfp", "fomc", "other"],
}

# Mapping from setup_type -> valid detail values (used for cross-validation)
SETUP_DETAIL_MAP: Final[dict[str, list[str]]] = {
    "liquidity_sweep": LIQUIDITY_SWEEP_DETAILS,
    "unmitigated_fvg": UNMITIGATED_FVG_DETAILS,
    "continuation": CONTINUATION_DETAILS,
    "other": [],  # no detail required for "other"
}


def validate_detail_in_map(
    type_value: str | None, detail_value: str | None, detail_map: dict[str, list[str]],
) -> None:
    """Raise ValueError if detail_value does not belong to type_value's allowed list."""
    if type_value is None or detail_value is None:
        return
    allowed = detail_map.get(type_value, [])
    if allowed and detail_value not in allowed:
        raise ValueError(
            f"detail '{detail_value}' is not valid for type '{type_value}'. Must be one of {allowed}",
        )


def validate_setup_detail(setup_type: str | None, setup_detail: str | None) -> None:
    """Raise ValueError if setup_detail does not belong to setup_type's allowed list.

    Shared by trade schemas (ict_setup_type/ict_setup_detail) and premarket scenario
    schemas (reaction_setup_type/reaction_setup_detail) — same taxonomy, same rule.
    """
    validate_detail_in_map(setup_type, setup_detail, SETUP_DETAIL_MAP)


def validate_tp_target_detail(tp_target: str | None, tp_target_detail: str | None) -> None:
    """Raise ValueError if tp_target_detail does not belong to tp_target's allowed list."""
    validate_detail_in_map(tp_target, tp_target_detail, TP_TARGET_DETAIL_MAP)

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
    "30s",
    "1m",
    "2m",
    "3m",
    "4m",
    "5m",
]

# --- Pre-market routine taxonomy ---

# Daily bias itself (distinct from HTF_BIAS_VALUES, which is alignment-to-bias)
DAILY_BIAS_VALUES: Final[list[str]] = ["bullish", "bearish", "neutral"]

# PD array type (distinct from PD_ARRAY_VALUES, which is premium/discount/equilibrium position)
PD_ARRAY_TYPES: Final[list[str]] = ["order_block", "fvg", "breaker", "rejection_block", "other"]

# Scenario outcome — set manually at review time, never auto-derived from trade P&L
SCENARIO_OUTCOME: Final[list[str]] = ["played_out", "partial", "invalidated", "never_triggered"]

# Was the daily bias correct, graded at review time
BIAS_CORRECT: Final[list[str]] = ["yes", "no", "partial"]

# Did the trader follow their own plan, graded at review time
EXECUTION_GRADES: Final[list[str]] = ["yes", "mostly", "no"]

# Emotional/behavioral tags for the review — distinct from FEELING_VALUES
EMOTION_TAGS: Final[list[str]] = [
    "fomo",
    "revenge",
    "overtrading",
    "early_exit",
    "hesitation",
    "other",
]

# Liquidity level taxonomy — shared by a scenario's condition (the level swept first)
# and target (the DOL aimed at). Same type+detail shape as SETUP_TYPES/SETUP_DETAIL_MAP.
LEVEL_TYPES: Final[list[str]] = ["session_high_low", "htf_high_low", "fvg", "other"]

# A specific session/killzone's high or low
SESSION_HIGH_LOW_DETAILS: Final[list[str]] = [
    "asia_high",
    "asia_low",
    "london_high",
    "london_low",
    "data_high",
    "data_low",
    "other",
]

# A candle high/low at a given timeframe, from intraday up through all-time
HTF_HIGH_LOW_DETAILS: Final[list[str]] = [
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
    "1w_high",
    "1w_low",
    "ath",
    "other",
]

# FVG at a given timeframe
LEVEL_FVG_DETAILS: Final[list[str]] = ["3m", "5m", "15m", "30m", "1h", "2h", "4h", "other"]

# Mapping from level_type -> valid detail values (used for cross-validation)
LEVEL_DETAIL_MAP: Final[dict[str, list[str]]] = {
    "session_high_low": SESSION_HIGH_LOW_DETAILS,
    "htf_high_low": HTF_HIGH_LOW_DETAILS,
    "fvg": LEVEL_FVG_DETAILS,
    "other": [],
}


def validate_level_detail(level_type: str | None, level_detail: str | None) -> None:
    """Raise ValueError if level_detail does not belong to level_type's allowed list."""
    validate_detail_in_map(level_type, level_detail, LEVEL_DETAIL_MAP)
