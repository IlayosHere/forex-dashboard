"""
api/routes/mistakes.py
----------------------
CRUD endpoints for the common mistakes tracker.

GET    /api/mistakes                    - list all mistakes, ordered by count DESC
POST   /api/mistakes                    - create a mistake (count=1); 409 on duplicate name
POST   /api/mistakes/{mistake_id}/increment - bump count + update last_occurred_at
DELETE /api/mistakes/{mistake_id}       - delete a mistake (204)
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import MistakeModel
from api.schemas_mistake import MistakeCreateRequest, MistakeResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/mistakes", response_model=list[MistakeResponse])
def list_mistakes(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MistakeModel]:
    """Return all mistakes for the current user, ordered by count DESC then recency."""
    stmt = (
        select(MistakeModel)
        .where(MistakeModel.owner == current_user)
        .order_by(MistakeModel.count.desc(), MistakeModel.last_occurred_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.post("/mistakes", response_model=MistakeResponse, status_code=201)
def create_mistake(
    req: MistakeCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MistakeModel:
    """Create a new mistake entry with count=1; 409 if name already exists (case-insensitive)."""
    name_lower = req.name.lower()
    existing = db.scalar(
        select(MistakeModel).where(
            MistakeModel.owner == current_user,
            func.lower(MistakeModel.name) == name_lower,
        )
    )
    if existing is not None:
        logger.warning("Duplicate mistake name for user %s: %s", current_user, req.name)
        raise HTTPException(status_code=409, detail="Mistake already exists")

    now = datetime.now(timezone.utc)
    mistake = MistakeModel(
        id=str(uuid.uuid4()),
        owner=current_user,
        name=req.name,
        count=1,
        last_occurred_at=now,
        created_at=now,
    )
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    logger.info("Mistake created: %s for user %s", mistake.id, current_user)
    return mistake


@router.post("/mistakes/{mistake_id}/increment", response_model=MistakeResponse)
def increment_mistake(
    mistake_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MistakeModel:
    """Increment the count of a mistake by 1 and update last_occurred_at to now."""
    mistake = db.get(MistakeModel, mistake_id)
    if mistake is None or mistake.owner != current_user:
        logger.warning("Mistake not found for increment: %s", mistake_id)
        raise HTTPException(status_code=404, detail="Mistake not found")

    mistake.count += 1
    mistake.last_occurred_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(mistake)
    logger.info("Mistake incremented: %s count=%d", mistake_id, mistake.count)
    return mistake


@router.delete("/mistakes/{mistake_id}", status_code=204)
def delete_mistake(
    mistake_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a mistake by ID, return 404 if not found."""
    mistake = db.get(MistakeModel, mistake_id)
    if mistake is None or mistake.owner != current_user:
        logger.warning("Mistake not found for deletion: %s", mistake_id)
        raise HTTPException(status_code=404, detail="Mistake not found")
    db.delete(mistake)
    db.commit()
    logger.info("Mistake deleted: %s", mistake_id)
