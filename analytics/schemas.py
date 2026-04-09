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
    resolution: str
    resolution_candles: int | None

    params: dict[str, Any]


class EnrichedListResponse(BaseModel):
    """Response for GET /api/analytics/enriched."""

    items: list[EnrichedSignalResponse]
    total: int


# ---------------------------------------------------------------------------
# Stats endpoint responses
# ---------------------------------------------------------------------------


class BucketWinRateResponse(BaseModel):
    """Win rate statistics for a single bucket."""

    bucket_label: str
    wins: int
    losses: int
    total: int
    win_rate: float
    ci_lower: float
    ci_upper: float


class UnivariateReportResponse(BaseModel):
    """Response for GET /api/analytics/univariate/{param_name}."""

    param_name: str
    dtype: str
    strategy: str
    total_signals: int
    buckets: list[BucketWinRateResponse]
    chi_squared: float | None = None
    chi_p_value: float | None = None
    correlation: float | None = None
    correlation_p_value: float | None = None


class CorrelationItem(BaseModel):
    """Single parameter correlation result."""

    param_name: str
    correlation: float
    p_value: float
    significant: bool


class SummaryResponse(BaseModel):
    """Response for GET /api/analytics/summary."""

    strategy: str
    total_resolved: int
    win_rate_overall: float
    params_analyzed: int
    top_correlations: list[CorrelationItem]
