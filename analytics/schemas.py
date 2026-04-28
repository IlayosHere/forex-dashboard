"""
analytics/schemas.py
--------------------
Pydantic v2 response models for the analytics API.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ParamInfo(BaseModel):
    """Metadata about a single registered parameter."""

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str
    strategies: list[str]
    needs_candles: bool


class ParamListResponse(BaseModel):
    """Response for GET /api/analytics/parameters."""

    model_config = ConfigDict(from_attributes=True)

    items: list[ParamInfo]
    total: int


class EnrichedSignalResponse(BaseModel):
    """Single enriched signal with original fields + derived params."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy: str
    symbol: str
    direction: str
    candle_time: datetime
    entry: float
    sl: float
    tp: float
    risk_pips: float
    spread_pips: float
    resolution: str | None
    resolution_candles: int | None

    params: dict[str, Any]


class EnrichedListResponse(BaseModel):
    """Response for GET /api/analytics/enriched."""

    model_config = ConfigDict(from_attributes=True)

    items: list[EnrichedSignalResponse]
    total: int


# ---------------------------------------------------------------------------
# Stats endpoint responses
# ---------------------------------------------------------------------------


class BucketWinRateResponse(BaseModel):
    """Win rate statistics for a single bucket."""

    model_config = ConfigDict(from_attributes=True)

    bucket_label: str
    wins: int
    losses: int
    total: int
    win_rate: float
    ci_lower: float
    ci_upper: float


class UnivariateReportResponse(BaseModel):
    """Response for GET /api/analytics/univariate/{param_name}."""

    model_config = ConfigDict(from_attributes=True)

    param_name: str
    dtype: str
    strategy: str
    total_signals: int
    buckets: list[BucketWinRateResponse]
    chi_squared: float | None = None
    chi_p_value: float | None = None
    correlation: float | None = None
    correlation_p_value: float | None = None
    delta: float | None = None
    ci_lo: float | None = None
    ci_hi: float | None = None
    best_bucket: str | None = None
    level: str | None = None


class CorrelationItem(BaseModel):
    """Single parameter correlation result."""

    model_config = ConfigDict(from_attributes=True)

    param_name: str
    correlation: float | None = None
    p_value: float | None = None
    delta: float | None = None
    ci_lo: float | None = None
    ci_hi: float | None = None
    best_bucket: str | None = None
    level: str | None = None
    fdr_status: str = "insufficient_data"


class SummaryResponse(BaseModel):
    """Response for GET /api/analytics/summary."""

    model_config = ConfigDict(from_attributes=True)

    strategy: str
    total_resolved: int
    win_rate_overall: float
    params_analyzed: int
    top_correlations: list[CorrelationItem]
    partial: bool = False
    excluded_params: list[str] = []


# ---------------------------------------------------------------------------
# Regime detection responses
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Interaction heatmap responses
# ---------------------------------------------------------------------------


class InteractionCell(BaseModel):
    """Win/loss counts and win rate for a single (bucket_a, bucket_b) cell."""

    model_config = ConfigDict(from_attributes=True)

    bucket_a: str
    bucket_b: str
    wins: int
    losses: int
    total: int
    win_rate: float | None  # None when total < 15 (sparse cell)


class InteractionResponse(BaseModel):
    """Response for GET /api/analytics/interaction."""

    model_config = ConfigDict(from_attributes=True)

    strategy: str
    param_a: str
    param_b: str
    buckets_a: list[str]
    buckets_b: list[str]
    cells: list[InteractionCell]
    total_signals: int
    overall_win_rate: float


class TopCombination(BaseModel):
    """One ranked (param_a × bucket_a) ∧ (param_b × bucket_b) combination."""

    model_config = ConfigDict(from_attributes=True)

    rank: int
    param_a: str
    bucket_a: str
    param_b: str
    bucket_b: str
    wins: int
    losses: int
    total: int
    win_rate: float
    edge: float
    direction: str
    ci_lo_raw: float
    ci_hi_raw: float
    ci_lo_adjusted: float
    ci_hi_adjusted: float
    score: float


class TopCombinationsResponse(BaseModel):
    """Response for GET /api/analytics/top-combinations."""

    model_config = ConfigDict(from_attributes=True)

    strategy: str
    symbol: str | None = None
    total_signals: int
    overall_win_rate: float
    confirmed_param_count: int
    pairs_scanned: int
    cells_evaluated: int
    items: list[TopCombination]
    reason: str | None = None


class ScoreContributor(BaseModel):
    """Single parameter's contribution to the composite quality score."""

    model_config = ConfigDict(from_attributes=True)

    param_name: str
    bucket: str | None
    indicator: int
    weight: int


class ScoreResponse(BaseModel):
    """Response for GET /api/analytics/score/{signal_id}."""

    model_config = ConfigDict(from_attributes=True)

    signal_id: str
    score: int
    max_possible: int
    contributing: list[ScoreContributor]
    explanation: str
    confirmed_params_used: int


class RegimeWindowStats(BaseModel):
    """Win-rate stats for one 30-signal window."""

    model_config = ConfigDict(from_attributes=True)

    n: int
    win_rate: float
    wins: int


class RegimeResponse(BaseModel):
    """Response for GET /api/analytics/regime."""

    model_config = ConfigDict(from_attributes=True)

    strategy: str
    symbol: str | None
    recent: RegimeWindowStats
    prior: RegimeWindowStats
    delta: float
    z_score: float | None
    status: str
    sufficient_data: bool
