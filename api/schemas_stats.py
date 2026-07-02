"""
api/schemas_stats.py
--------------------
Pydantic v2 response models for the extended statistics endpoints.

Split from schemas_trade.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from datetime import datetime
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


class IctIfvgBarsRow(BaseModel):
    """Single cell in the bars-to-IFVG × timeframe matrix."""

    model_config = ConfigDict(from_attributes=True)

    bars_label: str       # "1", "2", ..., "10", "10+"
    timeframe: str        # ict_ifvg_timeframe value e.g. "1m", "3m"
    total: int
    wins: int
    losses: int
    win_rate: float | None
    total_pnl_usd: float
    avg_pnl_usd: float | None
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
    by_killzone: dict[str, IctBucketStats]
    boolean_flags: dict[str, IctBooleanComparison]
    combo_matrix: list[IctComboEntry]
    ifvg_bars_matrix: list[IctIfvgBarsRow] = Field(default_factory=list)


class RDistributionBin(BaseModel):
    """Single bin in the R-multiple distribution histogram."""

    model_config = ConfigDict(from_attributes=True)

    bucket_label: str
    count: int
    pct: float


class DrawdownStats(BaseModel):
    """Drawdown and streak statistics for backtest mode."""

    model_config = ConfigDict(from_attributes=True)

    max_drawdown_r: float
    max_losing_streak: int
    expected_max_streak: float | None = None
    recovery_factor: float | None = None


class RobustnessStats(BaseModel):
    """Edge robustness: outlier-trimmed PF and trade concentration."""

    model_config = ConfigDict(from_attributes=True)

    profit_factor_ex_outliers: float | None = None
    largest_trade_pct_of_pnl: float | None = None


class ExpectancyCi(BaseModel):
    """95% confidence interval around mean R (expectancy)."""

    model_config = ConfigDict(from_attributes=True)

    expectancy_r: float | None = None
    expectancy_r_ci_low: float | None = None
    expectancy_r_ci_high: float | None = None
    edge_significant: bool | None = None


class RollingPfPoint(BaseModel):
    """Single point in the rolling profit factor series."""

    model_config = ConfigDict(from_attributes=True)

    index: int
    profit_factor: float | None = None


class EquityCurvePoint(BaseModel):
    """Single point on the equity curve."""

    model_config = ConfigDict(from_attributes=True)

    date: str | None
    close_time: str | None
    pnl_usd: float
    pnl_pips: float = Field(serialization_alias="pnl_points")
    pnl_r: float = 0.0
    cumulative_pnl_usd: float
    cumulative_pnl_pips: float = Field(serialization_alias="cumulative_pnl_points")
    cumulative_r: float = 0.0
    trade_count: int
    outcome: str | None


class DrawdownMetrics(BaseModel):
    """Live-account drawdown metrics."""

    model_config = ConfigDict(from_attributes=True)

    max_drawdown_usd: float = 0.0
    max_drawdown_r: float = 0.0
    current_drawdown_usd: float = 0.0
    current_drawdown_pct: float = 0.0
    drawdown_trade_count: int = 0
    recovery_factor: float | None = None


class RollingExpectancyPoint(BaseModel):
    """Single point in the rolling expectancy series."""

    model_config = ConfigDict(from_attributes=True)

    index: int
    close_time: datetime
    rolling_expectancy_r: float


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
    total_r: float = 0.0
    total_pnl_pips: float = Field(serialization_alias="total_pnl_points")
    total_pnl_usd: float
    best_trade_pnl: float | None
    worst_trade_pnl: float | None
    current_streak: int
    profit_factor: float | None
    avg_hold_time_hours: float | None
    avg_win_pips: float | None = Field(default=None, serialization_alias="avg_win_points")
    avg_loss_pips: float | None = Field(default=None, serialization_alias="avg_loss_points")
    avg_win_usd: float | None = None
    avg_loss_usd: float | None = None
    expectancy_usd: float | None = None
    expectancy_pips: float | None = Field(default=None, serialization_alias="expectancy_points")
    consistency_ratio: float | None = None
    by_strategy: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_symbol: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_account: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_day_of_week: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_session: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_confidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_rating: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_rule_compliance: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_criteria_met: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # BE outcome breakdown — counts only trades with outcome='breakeven'
    be_outcome_breakdown: dict[str, int] = Field(default_factory=dict)
    # Location breakdown — live trades only (backtest/legacy trades have None → excluded)
    by_location: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Backtest-mode robustness fields (populated only when account_type="backtest")
    r_distribution: list[RDistributionBin] = Field(default_factory=list)
    drawdown: DrawdownStats | None = None
    robustness: RobustnessStats | None = None
    expectancy_ci: ExpectancyCi | None = None
    # News/holiday breakdowns — populated for every account type
    by_news_day: dict[str, dict[str, Any]] = Field(default_factory=dict)
    by_market_holiday: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Latest date the hand-maintained news/holiday tables are confirmed through —
    # see shared/economic_calendar.py / shared/market_holidays.py. Trades after
    # this date aren't "confirmed no news," the table just isn't extended that far.
    news_data_coverage_through: str | None = None
    holiday_data_coverage_through: str | None = None
    # Live-mode metrics (populated for all account types)
    live_drawdown: DrawdownMetrics | None = None
    avg_tp_capture_pct: float | None = None
    tp_capture_sample_size: int = 0


class DailySummaryPoint(BaseModel):
    """Daily aggregated stats for calendar heatmap."""

    model_config = ConfigDict(from_attributes=True)

    date: str
    trades: int
    wins: int
    losses: int
    breakevens: int
    pnl_usd: float
    pnl_pips: float = Field(serialization_alias="pnl_points")
    pnl_r: float = 0.0
    compliant: int = 0
    mistakes: int = 0
