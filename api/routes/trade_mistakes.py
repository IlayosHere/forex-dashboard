"""
api/routes/trade_mistakes.py
----------------------------
Endpoints for linking/unlinking mistake vocabulary entries to trades.

POST   /api/trades/{trade_id}/mistakes            - link a mistake to a trade
DELETE /api/trades/{trade_id}/mistakes/{mistake_id} - unlink a mistake from a trade
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import MistakeModel, TradeMistakeModel, TradeModel
from api.schemas_trade import LinkedMistake

logger = logging.getLogger(__name__)

router = APIRouter()

_MIN_NAME_LEN: int = 1
_MAX_NAME_LEN: int = 200


class LinkMistakeRequest(BaseModel):
    """Body for POST /api/trades/{trade_id}/mistakes."""

    model_config = ConfigDict(extra="forbid")

    mistake_id: str | None = None
    name: str | None = Field(default=None, min_length=_MIN_NAME_LEN, max_length=_MAX_NAME_LEN)


def _get_owned_trade(trade_id: str, owner: str, db: Session) -> TradeModel:
    """Return trade or raise 404 if not found/not owned."""
    trade = db.get(TradeModel, trade_id)
    if trade is None or trade.owner != owner:
        logger.warning("Trade not found: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


def _get_linked_mistakes(trade_id: str, db: Session) -> list[dict[str, Any]]:
    """Return all LinkedMistake dicts currently linked to a trade."""
    rows = list(db.scalars(
        select(TradeMistakeModel).where(TradeMistakeModel.trade_id == trade_id),
    ).all())
    if not rows:
        return []
    ids = [r.mistake_id for r in rows]
    mistakes = list(db.scalars(
        select(MistakeModel).where(MistakeModel.id.in_(ids)),
    ).all())
    return [{"id": m.id, "name": m.name} for m in mistakes]


def _find_or_create_mistake(
    name: str, owner: str, db: Session,
) -> MistakeModel:
    """Find an existing mistake by (owner, name) or create one with count=0."""
    existing = db.scalar(
        select(MistakeModel).where(
            MistakeModel.owner == owner,
            func.lower(MistakeModel.name) == name.lower(),
        )
    )
    if existing is not None:
        return existing
    now = datetime.now(timezone.utc)
    mistake = MistakeModel(
        id=str(uuid.uuid4()), owner=owner, name=name,
        count=0, last_occurred_at=now, created_at=now,
    )
    db.add(mistake)
    db.flush()
    logger.info("Mistake auto-created: %s for user %s", mistake.id, owner)
    return mistake


def _link_mistake(
    trade_id: str, mistake: MistakeModel, db: Session,
) -> None:
    """Insert TradeMistakeModel row and increment mistake count."""
    existing_link = db.get(TradeMistakeModel, (trade_id, mistake.id))
    if existing_link is not None:
        raise HTTPException(status_code=409, detail="Mistake already linked to this trade")
    db.add(TradeMistakeModel(
        trade_id=trade_id,
        mistake_id=mistake.id,
        linked_at=datetime.now(timezone.utc),
    ))
    mistake.count += 1
    mistake.last_occurred_at = datetime.now(timezone.utc)
    logger.info("Mistake %s linked to trade %s", mistake.id, trade_id)


@router.post(
    "/trades/{trade_id}/mistakes",
    response_model=list[LinkedMistake],
    status_code=200,
)
def link_mistake(
    trade_id: str,
    req: LinkMistakeRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Link a mistake to a trade by ID or name; create the mistake if name is new."""
    if req.mistake_id is None and req.name is None:
        raise HTTPException(status_code=422, detail="Provide mistake_id or name")

    _get_owned_trade(trade_id, current_user, db)

    if req.mistake_id is not None:
        mistake = db.get(MistakeModel, req.mistake_id)
        if mistake is None or mistake.owner != current_user:
            raise HTTPException(status_code=404, detail="Mistake not found")
    else:
        name = req.name or ""
        mistake = _find_or_create_mistake(name, current_user, db)

    _link_mistake(trade_id, mistake, db)
    db.commit()
    return _get_linked_mistakes(trade_id, db)


@router.delete("/trades/{trade_id}/mistakes/{mistake_id}", status_code=204)
def unlink_mistake(
    trade_id: str,
    mistake_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Unlink a mistake from a trade and decrement its count (floor 0)."""
    _get_owned_trade(trade_id, current_user, db)

    link = db.get(TradeMistakeModel, (trade_id, mistake_id))
    if link is None:
        raise HTTPException(status_code=404, detail="Mistake not linked to this trade")

    db.delete(link)

    mistake = db.get(MistakeModel, mistake_id)
    if mistake is not None:
        mistake.count = max(0, mistake.count - 1)
        logger.info("Mistake %s unlinked from trade %s count=%d", mistake_id, trade_id, mistake.count)

    db.commit()
