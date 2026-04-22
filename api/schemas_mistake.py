"""
api/schemas_mistake.py
----------------------
Pydantic v2 request/response models for the common mistakes tracker endpoints.

Split from api/schemas.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MistakeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=200)


class MistakeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    count: int
    last_occurred_at: datetime
    created_at: datetime

    @field_validator("last_occurred_at", "created_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes read from SQLite."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
