"""
api/schemas_session.py
----------------------
Pydantic v2 request/response models for the trading session journal endpoints.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator

from shared.feelings import FEELING_VALUES


def _validate_feeling(v: str | None) -> str | None:
    """Validate that a feeling value belongs to the known enum."""
    if v is not None and v not in FEELING_VALUES:
        raise ValueError(f"feeling must be one of {FEELING_VALUES}")
    return v


class SessionUpsertRequest(BaseModel):
    """Request body for creating or updating a session journal entry."""

    model_config = ConfigDict(extra="forbid")

    had_pre_session_plan: bool | None = None
    feeling_pre: str | None = None
    feeling_during: str | None = None
    feeling_post: str | None = None
    session_notes: str = ""

    @field_validator("feeling_pre", "feeling_during", "feeling_post")
    @classmethod
    def validate_feeling(cls, v: str | None) -> str | None:
        """Ensure feeling values belong to the known enum."""
        return _validate_feeling(v)


class SessionResponse(BaseModel):
    """Response shape for a session journal entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner: str
    date: date
    had_pre_session_plan: bool | None
    feeling_pre: str | None
    feeling_during: str | None
    feeling_post: str | None
    session_notes: str
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes from SQLite."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
