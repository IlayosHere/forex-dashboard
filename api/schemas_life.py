"""
api/schemas_life.py
-------------------
Pydantic v2 request/response schemas for the Life Journal endpoints.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from shared.life_moods import LIFE_MOOD_VALUES


class LifeEntryCreateRequest(BaseModel):
    """Payload for POST /api/life/entries."""

    body: str = Field(..., min_length=1)
    mood: str | None = Field(None)
    tags: list[str] = Field(default_factory=list)
    entry_at: datetime | None = Field(None)

    def validate_mood(self) -> None:
        if self.mood is not None and self.mood not in LIFE_MOOD_VALUES:
            raise ValueError(f"mood must be one of {LIFE_MOOD_VALUES}")


class LifeEntryUpdateRequest(BaseModel):
    """Payload for PUT /api/life/entries/{id}."""

    body: str | None = Field(None, min_length=1)
    mood: str | None = Field(None)
    tags: list[str] | None = Field(None)
    entry_at: datetime | None = Field(None)
    clear_mood: bool = Field(False)


class LifeEntryResponse(BaseModel):
    """Response shape for a single life journal entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner: str
    body: str
    mood: str | None
    tags: list[str]
    entry_at: datetime
    created_at: datetime
    updated_at: datetime


class LifeSummaryPoint(BaseModel):
    """One day's summary used for the calendar heatmap."""

    date: str
    count: int
    dominant_mood: str | None
