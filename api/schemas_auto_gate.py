"""
api/schemas_auto_gate.py
------------------------
Pydantic schemas for the auto-gate optimizer endpoints.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_MIN_PASS_RATE = 0.40


class OptimizeRequest(BaseModel):
    """Request body for the gate optimizer."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    min_pass_rate: float = Field(default=_DEFAULT_MIN_PASS_RATE, ge=0.0, le=1.0)
    dry_run: bool = True


class OptimizeResponse(BaseModel):
    """Optimizer result — conditions selected and performance stats."""

    model_config = ConfigDict()

    strategy: str
    conditions_selected: list[dict[str, Any]]
    win_rate_baseline: float | None
    win_rate_optimized: float | None
    delta: float | None
    pass_rate: float | None
    pass_count: int
    total_signals: int
    confirmed_params_found: int
    dry_run: bool
    gate_set_id: str | None
    reason: str | None


class RecomputeGradesRequest(BaseModel):
    """Request body for the grade recompute endpoint."""

    model_config = ConfigDict(extra="forbid")

    strategy: str


class RecomputeGradesResponse(BaseModel):
    """Result of the grade recompute operation."""

    model_config = ConfigDict()

    strategy: str
    recomputed: int
