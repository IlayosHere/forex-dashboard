"""
api/schemas_rule.py
-------------------
Pydantic v2 request/response models for trading rules and rule categories.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryResponse(BaseModel):
    """A rule category as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes read from SQLite."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class CategoryCreateRequest(BaseModel):
    """Body for POST /api/rule-categories."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)


class CategoryUpdateRequest(BaseModel):
    """Body for PUT /api/rule-categories/{id}."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)


class LinkedMistakeRef(BaseModel):
    """A mistake linked to a rule — id + name only."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class RuleResponse(BaseModel):
    """A trading rule as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    body: str | None
    break_count: int
    created_at: datetime
    updated_at: datetime
    category: CategoryResponse | None
    linked_mistakes: list[LinkedMistakeRef]

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes read from SQLite."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class RuleCreateRequest(BaseModel):
    """Body for POST /api/rules."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=80)
    body: str | None = None
    category_id: str | None = None
    linked_mistake_ids: list[str] = Field(default_factory=list)


class RuleUpdateRequest(BaseModel):
    """Body for PUT /api/rules/{id} — all fields optional."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=80)
    body: str | None = None
    category_id: str | None = None
    linked_mistake_ids: list[str] | None = None
