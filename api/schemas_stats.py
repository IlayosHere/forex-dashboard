"""
api/schemas_stats.py
--------------------
Pydantic v2 response models for the extended statistics endpoints.

Split from schemas_trade.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    expectancy_r: float | None


class IctBooleanComparison(BaseModel):
    """True/false split for a single boolean ICT flag."""

    model_config = ConfigDict(from_attributes=True)

    true: IctBucketStats
    false: IctBucketStats


class IctComboEntry(BaseModel):
    """Single row in the setup_type x session x htf_bias combo matrix."""

    model_config = ConfigDict(from_attributes=True)

    setup_type: str
    mnq_session: str | None
    htf_bias: str | None
    total: int
    wins: int
    losses: int
    win_rate: float | None
    total_pnl_usd: float
    avg_rr: float | None
    expectancy_r: float | None


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
    by_htf_bias: dict[str, IctBucketStats]
    by_entry_model: dict[str, IctBucketStats]
    by_pd_array: dict[str, IctBucketStats]
    by_killzone: dict[str, IctBucketStats]
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


class TradeStatsResponse(BaseModel):
    """Aggregated trade journal statistics for the /trades/stats endpoint."""

    model_config = ConfigDict(from_attributes=True)

    total_trades: int
    open_trades: int
    closed_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate: float | None
    avg_rr: float | None
    total_pnl_pips: float
    total_pnl_usd: float
    best_trade_pnl: float | None
    worst_trade_pnl: float | None
    current_streak: int
    profit_factor: float | None
    avg_hold_time_hours: float | None
    avg_win_pips: float | None = None
    avg_loss_pips: float | None = None
    avg_win_usd: float | None = None
    avg_loss_usd: float | None = None
    expectancy_usd: float | None = None
    expectancy_pips: float | None = None
    consistency_ratio: float | None = None
    by_strategy: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_symbol: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_account: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_day_of_week: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_session: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_confidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_rating: dict[str, dict[str, Any]] = Field(default_factory=dict)


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
