"""
api/schemas_premarket.py
-------------------------
Pydantic v2 request/response models for the pre-market routine endpoints.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.ict_taxonomy import (
    DAILY_BIAS_VALUES,
    EXECUTION_GRADES,
    LEVEL_DETAIL_MAP,
    LEVEL_TYPES,
    PD_ARRAY_TYPES,
    PD_ARRAY_VALUES,
    SCENARIO_OUTCOME,
    SETUP_DETAIL_MAP,
    SETUP_TYPES,
    validate_level_detail,
    validate_setup_detail,
)


class PlanUpsertRequest(BaseModel):
    """Request body for creating or updating a pre-market plan."""

    model_config = ConfigDict(extra="forbid")

    weekly_dealing_range: str | None = None
    weekly_dol: str | None = None
    weekly_opening_gap: str | None = None
    daily_bias: str | None = None
    daily_bias_signals: dict[str, Any] = Field(default_factory=dict)
    h4_pd_array: str | None = None
    h4_pd_location: str | None = None
    h1_zone: str | None = None
    h1_structure: str | None = None
    ltf_notes: str | None = None
    narrative: str = ""

    @field_validator("weekly_dealing_range")
    @classmethod
    def validate_weekly_dealing_range(cls, v: str | None) -> str | None:
        if v is not None and v not in PD_ARRAY_VALUES:
            raise ValueError(f"weekly_dealing_range must be one of {PD_ARRAY_VALUES}")
        return v

    @field_validator("daily_bias")
    @classmethod
    def validate_daily_bias(cls, v: str | None) -> str | None:
        if v is not None and v not in DAILY_BIAS_VALUES:
            raise ValueError(f"daily_bias must be one of {DAILY_BIAS_VALUES}")
        return v

    @field_validator("h4_pd_array")
    @classmethod
    def validate_h4_pd_array(cls, v: str | None) -> str | None:
        if v is not None and v not in PD_ARRAY_TYPES:
            raise ValueError(f"h4_pd_array must be one of {PD_ARRAY_TYPES}")
        return v


class ScenarioCreateRequest(BaseModel):
    """Request body for adding a scenario to a pre-market plan.

    The trade: an area to take it from (`reaction_setup_type`/`reaction_setup_detail`,
    reusing the exact taxonomy as trade entries — ict_setup_type/ict_setup_detail — so a
    scenario can later be compared directly against the trade it produced) into a DOL
    (`target_level_*` — external liquidity = a high/low, internal liquidity = an FVG).
    `notes` is free text for anything the structured fields don't capture.
    """

    model_config = ConfigDict(extra="forbid")

    reaction_setup_type: str | None = None
    reaction_setup_detail: str | None = None
    target_level_type: str | None = None
    target_level_detail: str | None = None
    notes: str = ""

    @field_validator("target_level_type")
    @classmethod
    def validate_level_type(cls, v: str | None) -> str | None:
        if v is not None and v not in LEVEL_TYPES:
            raise ValueError(f"level_type must be one of {LEVEL_TYPES}")
        return v

    @field_validator("target_level_detail")
    @classmethod
    def validate_level_detail_value(cls, v: str | None) -> str | None:
        all_details = [d for details in LEVEL_DETAIL_MAP.values() for d in details]
        if v is not None and v not in all_details:
            raise ValueError(f"level_detail must be one of {all_details}")
        return v

    @field_validator("reaction_setup_type")
    @classmethod
    def validate_reaction_setup_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SETUP_TYPES:
            raise ValueError(f"reaction_setup_type must be one of {SETUP_TYPES}")
        return v

    @field_validator("reaction_setup_detail")
    @classmethod
    def validate_reaction_setup_detail(cls, v: str | None) -> str | None:
        all_details = [d for details in SETUP_DETAIL_MAP.values() for d in details]
        if v is not None and v not in all_details:
            raise ValueError(f"reaction_setup_detail must be one of {all_details}")
        return v

    @model_validator(mode="after")
    def validate_details_match_types(self) -> "ScenarioCreateRequest":
        validate_setup_detail(self.reaction_setup_type, self.reaction_setup_detail)
        validate_level_detail(self.target_level_type, self.target_level_detail)
        return self


class ScenarioUpdateRequest(ScenarioCreateRequest):
    """Request body for editing a scenario — same fields as create, plus the outcome
    quick-set (played_out/partial/invalidated/never_triggered), settable independently
    of the full review screen."""

    outcome_status: str | None = None

    @field_validator("outcome_status")
    @classmethod
    def validate_outcome_status(cls, v: str | None) -> str | None:
        if v is not None and v not in SCENARIO_OUTCOME:
            raise ValueError(f"outcome_status must be one of {SCENARIO_OUTCOME}")
        return v


class CheckpointCreateRequest(BaseModel):
    """Request body for appending a during-session checkpoint note to a plan."""

    model_config = ConfigDict(extra="forbid")

    note: str


class ReviewUpsertRequest(BaseModel):
    """Request body for the post-session review of a plan.

    Only `execution_grade` ("did you follow your plan?") is exposed today.
    `bias_correct`/`emotion_tags` exist on the model for a future fuller review screen.
    """

    model_config = ConfigDict(extra="forbid")

    execution_grade: str | None = None

    @field_validator("execution_grade")
    @classmethod
    def validate_execution_grade(cls, v: str | None) -> str | None:
        if v is not None and v not in EXECUTION_GRADES:
            raise ValueError(f"execution_grade must be one of {EXECUTION_GRADES}")
        return v


class ReviewResponse(BaseModel):
    """Response shape for a plan's post-session review."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    bias_correct: str | None
    execution_grade: str | None
    emotion_tags: list[str]
    review_notes: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class PremarketDaySummary(BaseModel):
    """Lightweight per-date summary for the calendar grid — no nested scenario detail."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    daily_bias: str | None
    scenario_count: int


class ScenarioResponse(BaseModel):
    """Response shape for a single plan scenario."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    # The parent plan's date — lets the UI link from a scenario (or a trade linked to
    # it) back to that day's page without a second lookup.
    date: date
    reaction_setup_type: str | None
    reaction_setup_detail: str | None
    target_level_type: str | None
    target_level_detail: str | None
    notes: str
    outcome_status: str | None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class PlanResponse(BaseModel):
    """Response shape for a pre-market plan, including its scenarios.

    `scenarios` is NOT an ORM-loaded relationship (lazy="noload") — it must be
    populated explicitly by the route handler, never via model_validate(plan) alone.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner: str
    date: date
    weekly_dealing_range: str | None
    weekly_dol: str | None
    weekly_opening_gap: str | None
    daily_bias: str | None
    daily_bias_signals: dict[str, Any]
    h4_pd_array: str | None
    h4_pd_location: str | None
    h1_zone: str | None
    h1_structure: str | None
    ltf_notes: str | None
    narrative: str
    checkpoints: list[dict[str, Any]]
    scenarios: list[ScenarioResponse] = Field(default_factory=list)
    review: ReviewResponse | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
