"""
api/routes/sessions.py
----------------------
Session journal endpoints — one entry per trader per calendar date.

GET  /api/sessions/{date}   - fetch a session by date (404 if not logged yet)
PUT  /api/sessions/{date}   - upsert a session for a date (create or update)
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import TradingSessionModel
from api.schemas_session import SessionResponse, SessionUpsertRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_date(date_str: str) -> date:
    """Parse ISO date string YYYY-MM-DD, raise 422 on invalid format."""
    try:
        return date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {date_str!r}. Use YYYY-MM-DD") from exc


@router.get("/sessions/{date_str}", response_model=SessionResponse)
def get_session(
    date_str: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TradingSessionModel:
    """Fetch the session journal entry for a specific date. Returns 404 if not logged yet."""
    target_date = _parse_date(date_str)
    session = db.scalar(
        select(TradingSessionModel).where(
            TradingSessionModel.owner == current_user,
            TradingSessionModel.date == target_date,
        )
    )
    if session is None:
        logger.warning("Session not found for user %s on %s", current_user, date_str)
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.put("/sessions/{date_str}", response_model=SessionResponse)
def upsert_session(
    date_str: str,
    req: SessionUpsertRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TradingSessionModel:
    """Create or update the session journal entry for a specific date."""
    target_date = _parse_date(date_str)
    now = datetime.now(timezone.utc)

    session = db.scalar(
        select(TradingSessionModel).where(
            TradingSessionModel.owner == current_user,
            TradingSessionModel.date == target_date,
        )
    )

    if session is None:
        session = TradingSessionModel(
            id=str(uuid.uuid4()),
            owner=current_user,
            date=target_date,
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        logger.info("Session created for user %s on %s", current_user, date_str)
    else:
        session.updated_at = now
        logger.info("Session updated for user %s on %s", current_user, date_str)

    session.had_pre_session_plan = req.had_pre_session_plan
    session.feeling_pre = req.feeling_pre
    session.feeling_during = req.feeling_during
    session.feeling_post = req.feeling_post
    session.session_notes = req.session_notes

    db.commit()
    db.refresh(session)
    return session
