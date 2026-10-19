"""
api/schemas_stats_time.py
-------------------------
Pydantic v2 response models for the time-of-day edge analysis.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.schemas_stats import IctBucketStats, IctStatsResponse


class TimeMatrixCell(BaseModel):
    """One (row value x NY phase) cell of a cross-tab matrix."""

    model_config = ConfigDict(from_attributes=True)

    row: str
    phase: str
    stats: IctBucketStats


class TimeInsight(BaseModel):
    """A ranked strength or weakness cell worth acting on."""

    model_config = ConfigDict(from_attributes=True)

    kind: Literal["strength", "weakness"]
    dimension: str
    row: str
    phase: str
    stats: IctBucketStats


class TimeEdgeStats(BaseModel):
    """Time-of-day edge: where in the NY session each setup/timeframe works."""

    model_config = ConfigDict(from_attributes=True)

    by_ny_phase: dict[str, IctBucketStats]
    by_time_slice: dict[str, IctBucketStats]
    by_macro: dict[str, IctBucketStats]
    matrices: dict[str, list[TimeMatrixCell]] = Field(default_factory=dict)
    insights: list[TimeInsight] = Field(default_factory=list)
    min_sample: int


class IctStatsWithTimeResponse(IctStatsResponse):
    """ICT stats plus the time-of-day edge analysis."""

    time_edge: TimeEdgeStats | None = None
