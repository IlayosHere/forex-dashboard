"""
api/schemas_gates.py
--------------------
Pydantic v2 schemas for gates, grade thresholds, and experiments.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Operator = Literal["eq", "ne", "in", "not_in", "gte", "lte", "between", "is_null", "not_null"]


class GateConditionSchema(BaseModel):
    """A single AND-combined condition in a gate set or experiment."""

    model_config = ConfigDict(extra="forbid")

    param: str = Field(min_length=1)
    op: Operator
    value: Any = None
    values: list[Any] | None = None
    low: float | None = None
    high: float | None = None

    @model_validator(mode="after")
    def check_shape(self) -> "GateConditionSchema":
        """Enforce operator-specific required fields."""
        if self.op in ("in", "not_in") and not isinstance(self.values, list):
            raise ValueError(f"Operator '{self.op}' requires a 'values' list")
        if self.op == "between" and (self.low is None or self.high is None):
            raise ValueError("Operator 'between' requires 'low' and 'high'")
        if self.op in ("eq", "ne", "gte", "lte") and self.value is None:
            raise ValueError(f"Operator '{self.op}' requires a 'value'")
        return self


# ---------------------------------------------------------------------------
# Gate sets
# ---------------------------------------------------------------------------

class GateSetCreateRequest(BaseModel):
    """Create a new gate set (starts inactive)."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    conditions: list[GateConditionSchema]


class GateSetUpdateRequest(BaseModel):
    """Update name, description, or conditions of an existing gate set."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    conditions: list[GateConditionSchema] | None = None


class GateSetResponse(BaseModel):
    """Full gate set representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy: str
    name: str
    description: str | None
    is_active: bool
    conditions: list[GateConditionSchema]
    created_at: datetime
    updated_at: datetime


class GatePreviewRequest(BaseModel):
    """Evaluate conditions against historical signals without saving."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    conditions: list[GateConditionSchema]


class GatePreviewResponse(BaseModel):
    """Statistics for how a condition set would filter historical signals."""

    model_config = ConfigDict()

    total_signals_evaluated: int
    pass_count: int
    block_count: int
    pass_rate: float
    win_rate_passed: float | None
    win_rate_baseline: float | None
    delta_vs_baseline: float | None
    per_condition_failure_count: list[int]


# ---------------------------------------------------------------------------
# Grade thresholds
# ---------------------------------------------------------------------------

class GradeThresholdsResponse(BaseModel):
    """Current grade thresholds for a strategy."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy: str
    a_min: int
    b_min: int
    is_active: bool
    created_at: datetime


class GradeThresholdsUpdateRequest(BaseModel):
    """Update the A and B score thresholds for a strategy."""

    model_config = ConfigDict(extra="forbid")

    a_min: int = Field(ge=1, le=99)
    b_min: int = Field(ge=0, le=98)

    @model_validator(mode="after")
    def check_order(self) -> "GradeThresholdsUpdateRequest":
        if self.b_min >= self.a_min:
            raise ValueError("b_min must be less than a_min")
        return self


class GradeRecomputeRequest(BaseModel):
    """Request to retroactively recompute grades on historical signals."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    dry_run: bool = True


class GradeRecomputeResponse(BaseModel):
    """Result of a grade recompute run."""

    model_config = ConfigDict()

    strategy: str
    dry_run: bool
    recomputed: int


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

class ExperimentCreateRequest(BaseModel):
    """Create a new saved experiment definition."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    strategy: str
    conditions: list[GateConditionSchema]
    date_from: datetime | None = None
    date_to: datetime | None = None
    notes: str | None = None


class ExperimentUpdateRequest(BaseModel):
    """Update a saved experiment (clears last_summary to avoid stale data)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    conditions: list[GateConditionSchema] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    notes: str | None = None


class ExperimentResponse(BaseModel):
    """Full saved experiment representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    strategy: str
    conditions: list[GateConditionSchema]
    date_from: datetime | None
    date_to: datetime | None
    notes: str | None
    last_run_at: datetime | None
    last_summary: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class BucketStat(BaseModel):
    """Win-rate stats for one value bucket of a parameter."""

    model_config = ConfigDict()

    bucket: str
    n: int
    wins: int
    win_rate: float
    ci_lo: float
    ci_hi: float


class ParamBreakdown(BaseModel):
    """Per-bucket breakdown for one parameter referenced in experiment conditions."""

    model_config = ConfigDict()

    param_name: str
    buckets: list[BucketStat]


class ExperimentEvaluateRequest(BaseModel):
    """Ephemeral experiment evaluation — does not save."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    conditions: list[GateConditionSchema]
    date_from: datetime | None = None
    date_to: datetime | None = None


class ExperimentResultResponse(BaseModel):
    """Full evaluation result for an experiment run."""

    model_config = ConfigDict()

    strategy: str
    date_from: datetime | None
    date_to: datetime | None
    total_signals: int
    resolved_signals: int
    passing_signals: int
    resolved_passing: int
    win_rate_passed: float | None
    win_rate_baseline: float
    delta_vs_baseline: float | None
    per_condition_failure_count: list[int]
    per_param_breakdown: list[ParamBreakdown]
