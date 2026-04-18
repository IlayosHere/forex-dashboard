"""
api/schemas_stats.py
--------------------
Pydantic v2 response models for the extended statistics endpoints.

Split from schemas_trade.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# ICT stats schemas
# ---------------------------------------------------------------------------


class IctBucketStats(BaseModel):
    """Aggregated performance stats for a single ICT dimension bucket."""

    model_config = ConfigDict(from_attributes=True)

    total: int
    wins: int
    losses: int
    win_rate: float | None
    total_pnl_usd: float
    avg_pnl_usd: float | None
    avg_rr: float | None


class IctBooleanComparison(BaseModel):
    """True/false split for a single boolean ICT flag."""

    model_config = ConfigDict(from_attributes=True)

    true: IctBucketStats
    false: IctBucketStats


class IctComboEntry(BaseModel):
    """Single row in the setup_type x (smt_present, tdo_aligned) combo matrix."""

    model_config = ConfigDict(from_attributes=True)

    setup_type: str
    smt_present: bool | None
    tdo_aligned: bool | None
    total: int
    wins: int
    losses: int
    win_rate: float | None
    total_pnl_usd: float
    avg_rr: float | None


class IctStatsResponse(BaseModel):
    """Full ICT statistics response for MNQ futures trades."""

    model_config = ConfigDict(from_attributes=True)

    total_trades: int
    wins: int
    losses: int
    win_rate: float | None
    by_setup_type: dict[str, IctBucketStats]
    by_tp_target: dict[str, IctBucketStats]
    by_ifvg_timeframe: dict[str, IctBucketStats]
    by_mnq_session: dict[str, IctBucketStats]
    boolean_flags: dict[str, IctBooleanComparison]
    combo_matrix: list[IctComboEntry]


class EquityCurvePoint(BaseModel):
    """Single point on the equity curve."""

    model_config = ConfigDict(from_attributes=True)

    date: str | None
    close_time: str | None
    pnl_usd: float
    pnl_pips: float
    cumulative_pnl_usd: float
    cumulative_pnl_pips: float
    trade_count: int
    outcome: str | None


class DailySummaryPoint(BaseModel):
    """Daily aggregated stats for calendar heatmap."""

    model_config = ConfigDict(from_attributes=True)

    date: str
    trades: int
    wins: int
    losses: int
    breakevens: int
    pnl_usd: float
    pnl_pips: float
