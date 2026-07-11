"""
api/routes/life.py
------------------
Life Journal endpoints — personal entries with mood and tags.

GET    /api/life/entries              - list entries (filtered, paginated)
POST   /api/life/entries              - create a new entry
GET    /api/life/entries/{id}         - fetch a single entry
PUT    /api/life/entries/{id}         - update an entry
DELETE /api/life/entries/{id}         - delete an entry
GET    /api/life/summary              - daily counts + dominant mood (heatmap)
GET    /api/life/tags                 - all tags used by this user (autocomplete)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Text, cast, func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import LifeEntryModel
from api.schemas_life import (
    LifeEntryCreateRequest,
    LifeEntryResponse,
    LifeEntryUpdateRequest,
    LifeSummaryPoint,
)
from shared.life_moods import LIFE_MOOD_VALUES, dominant_mood

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_or_404(entry_id: str, owner: str, db: Session) -> LifeEntryModel:
    """Fetch a life entry by ID for the given owner, raise 404 if missing."""
    entry = db.scalar(
        select(LifeEntryModel).where(
            LifeEntryModel.id == entry_id,
            LifeEntryModel.owner == owner,
        )
    )
    if entry is None:
        logger.warning("Life entry not found: %s (user=%s)", entry_id, owner)
        raise HTTPException(status_code=404, detail="Life entry not found")
    return entry


@router.get("/life/entries", response_model=list[LifeEntryResponse])
def list_entries(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    mood: list[str] | None = Query(None),
    tag: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[LifeEntryModel]:
    """List life entries for the current user, newest first."""
    stmt = (
        select(LifeEntryModel)
        .where(LifeEntryModel.owner == current_user)
        .order_by(LifeEntryModel.entry_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if from_dt:
        stmt = stmt.where(LifeEntryModel.entry_at >= from_dt)
    if to_dt:
        stmt = stmt.where(LifeEntryModel.entry_at <= to_dt)
    if mood:
        stmt = stmt.where(LifeEntryModel.mood.in_(mood))
    if tag:
        # Cast JSON to text and search for the quoted tag so Postgres doesn't
        # reject the ~~ operator (json ~~ text is undefined in PG; text ~~ text works).
        # Wrapping in quotes prevents false positives from substring matches.
        stmt = stmt.where(cast(LifeEntryModel.tags, Text).contains(f'"{tag}"'))
    return list(db.scalars(stmt))


@router.post("/life/entries", response_model=LifeEntryResponse, status_code=201)
def create_entry(
    req: LifeEntryCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LifeEntryModel:
    """Create a new life journal entry."""
    if req.mood is not None and req.mood not in LIFE_MOOD_VALUES:
        raise HTTPException(status_code=422, detail=f"mood must be one of {LIFE_MOOD_VALUES}")
    now = datetime.now(timezone.utc)
    entry = LifeEntryModel(
        id=str(uuid.uuid4()),
        owner=current_user,
        body=req.body,
        mood=req.mood,
        tags=req.tags,
        entry_at=req.entry_at or now,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info("Life entry created: %s (user=%s)", entry.id, current_user)
    return entry


@router.get("/life/entries/{entry_id}", response_model=LifeEntryResponse)
def get_entry(
    entry_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LifeEntryModel:
    """Fetch a single life entry by ID."""
    return _get_or_404(entry_id, current_user, db)


@router.put("/life/entries/{entry_id}", response_model=LifeEntryResponse)
def update_entry(
    entry_id: str,
    req: LifeEntryUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> LifeEntryModel:
    """Update a life journal entry (partial — only provided fields change)."""
    entry = _get_or_404(entry_id, current_user, db)
    if req.mood is not None and req.mood not in LIFE_MOOD_VALUES:
        raise HTTPException(status_code=422, detail=f"mood must be one of {LIFE_MOOD_VALUES}")
    if req.body is not None:
        entry.body = req.body
    if req.clear_mood:
        entry.mood = None
    elif req.mood is not None:
        entry.mood = req.mood
    if req.tags is not None:
        entry.tags = req.tags
    if req.entry_at is not None:
        entry.entry_at = req.entry_at
    entry.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/life/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a life journal entry."""
    entry = _get_or_404(entry_id, current_user, db)
    db.delete(entry)
    db.commit()
    logger.info("Life entry deleted: %s (user=%s)", entry_id, current_user)


@router.get("/life/summary", response_model=list[LifeSummaryPoint])
def get_summary(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
) -> list[LifeSummaryPoint]:
    """Return per-day entry count and dominant mood for the calendar heatmap."""
    stmt = select(LifeEntryModel).where(LifeEntryModel.owner == current_user)
    if from_dt:
        stmt = stmt.where(LifeEntryModel.entry_at >= from_dt)
    if to_dt:
        stmt = stmt.where(LifeEntryModel.entry_at <= to_dt)
    entries = list(db.scalars(stmt))

    by_date: dict[str, list[str | None]] = {}
    for e in entries:
        day = e.entry_at.strftime("%Y-%m-%d")
        by_date.setdefault(day, []).append(e.mood)

    return [
        LifeSummaryPoint(
            date=day,
            count=len(moods),
            dominant_mood=dominant_mood([m for m in moods if m]),
        )
        for day, moods in sorted(by_date.items())
    ]


@router.get("/life/tags", response_model=list[str])
def get_tags(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[str]:
    """Return all unique tags used by this user across all life entries."""
    entries = list(db.scalars(
        select(LifeEntryModel).where(LifeEntryModel.owner == current_user)
    ))
    seen: set[str] = set()
    for e in entries:
        seen.update(e.tags)
    return sorted(seen)
