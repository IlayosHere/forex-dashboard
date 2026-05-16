"""
api/routes/rules.py
-------------------
CRUD endpoints for trading rules.

GET    /api/rules          - list rules, owner-scoped, sorted by break_count DESC
POST   /api/rules          - create a rule (201)
GET    /api/rules/{id}     - fetch a single rule
PUT    /api/rules/{id}     - update rule; syncs linked_mistake_ids + recomputes break_count
DELETE /api/rules/{id}     - delete rule (204)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import MistakeModel, RuleCategoryModel, RuleMistakeLink, RuleModel
from api.schemas_rule import RuleCreateRequest, RuleResponse, RuleUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _recompute_break_count(rule_id: str, db: Session) -> int:
    """Sum mistake.count for all mistakes linked to the given rule."""
    links = db.scalars(
        select(RuleMistakeLink).where(RuleMistakeLink.rule_id == rule_id)
    ).all()
    ids = [lnk.mistake_id for lnk in links]
    if not ids:
        return 0
    total = db.scalar(
        select(func.sum(MistakeModel.count)).where(MistakeModel.id.in_(ids))
    )
    return int(total or 0)


def recompute_rules_for_mistake(mistake_id: str, db: Session) -> None:
    """Recompute break_count on every rule linked to the given mistake."""
    links = db.scalars(
        select(RuleMistakeLink).where(RuleMistakeLink.mistake_id == mistake_id)
    ).all()
    for link in links:
        rule = db.get(RuleModel, link.rule_id)
        if rule is not None:
            rule.break_count = _recompute_break_count(link.rule_id, db)
    db.commit()


def _rule_to_response(rule: RuleModel, db: Session) -> dict[str, Any]:
    """Build a dict suitable for RuleResponse.model_validate()."""
    category: RuleCategoryModel | None = None
    if rule.category_id is not None:
        category = db.get(RuleCategoryModel, rule.category_id)

    links = db.scalars(
        select(RuleMistakeLink).where(RuleMistakeLink.rule_id == rule.id)
    ).all()
    linked_mistakes: list[dict[str, str]] = []
    if links:
        mistake_ids = [lnk.mistake_id for lnk in links]
        mistakes = db.scalars(
            select(MistakeModel).where(MistakeModel.id.in_(mistake_ids))
        ).all()
        linked_mistakes = [{"id": m.id, "name": m.name} for m in mistakes]

    return {
        "id": rule.id,
        "title": rule.title,
        "body": rule.body,
        "break_count": rule.break_count,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
        "category": category,
        "linked_mistakes": linked_mistakes,
    }


def _get_owned_rule(rule_id: str, owner: str, db: Session) -> RuleModel:
    """Return rule or raise 404 if not found / not owned."""
    rule = db.get(RuleModel, rule_id)
    if rule is None or rule.owner != owner:
        logger.warning("Rule not found: %s", rule_id)
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


def _sync_mistake_links(rule_id: str, new_ids: list[str], db: Session) -> None:
    """Full-replace linked mistakes: delete removed, insert new."""
    existing = db.scalars(
        select(RuleMistakeLink).where(RuleMistakeLink.rule_id == rule_id)
    ).all()
    existing_ids = {lnk.mistake_id for lnk in existing}
    new_set = set(new_ids)

    for lnk in existing:
        if lnk.mistake_id not in new_set:
            db.delete(lnk)

    now = datetime.now(timezone.utc)
    for mid in new_set - existing_ids:
        db.add(RuleMistakeLink(rule_id=rule_id, mistake_id=mid, linked_at=now))


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@router.get("/rules", response_model=list[RuleResponse])
def list_rules(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Return all rules for the current user, sorted by break_count DESC."""
    rules = db.scalars(
        select(RuleModel)
        .where(RuleModel.owner == current_user)
        .order_by(RuleModel.break_count.desc())
    ).all()
    return [_rule_to_response(r, db) for r in rules]


@router.post("/rules", response_model=RuleResponse, status_code=201)
def create_rule(
    req: RuleCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Create a trading rule, optionally linking mistakes and assigning a category."""
    now = datetime.now(timezone.utc)
    rule = RuleModel(
        id=str(uuid.uuid4()),
        owner=current_user,
        title=req.title,
        body=req.body,
        category_id=req.category_id,
        break_count=0,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    db.flush()

    if req.linked_mistake_ids:
        _sync_mistake_links(rule.id, req.linked_mistake_ids, db)
        db.flush()
        rule.break_count = _recompute_break_count(rule.id, db)

    db.commit()
    db.refresh(rule)
    logger.info("Rule created: %s for user %s", rule.id, current_user)
    return _rule_to_response(rule, db)


@router.get("/rules/{rule_id}", response_model=RuleResponse)
def get_rule(
    rule_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Fetch a single rule by ID; 404 if not found."""
    rule = _get_owned_rule(rule_id, current_user, db)
    return _rule_to_response(rule, db)


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    req: RuleUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Update a rule; full-replaces linked_mistake_ids and recomputes break_count."""
    rule = _get_owned_rule(rule_id, current_user, db)

    if req.title is not None:
        rule.title = req.title
    if req.body is not None:
        rule.body = req.body
    if req.category_id is not None:
        rule.category_id = req.category_id

    if req.linked_mistake_ids is not None:
        _sync_mistake_links(rule_id, req.linked_mistake_ids, db)
        db.flush()
        rule.break_count = _recompute_break_count(rule_id, db)

    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)
    logger.info("Rule updated: %s", rule_id)
    return _rule_to_response(rule, db)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(
    rule_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a rule by ID; cascade removes all mistake links."""
    rule = _get_owned_rule(rule_id, current_user, db)
    db.delete(rule)
    db.commit()
    logger.info("Rule deleted: %s", rule_id)
