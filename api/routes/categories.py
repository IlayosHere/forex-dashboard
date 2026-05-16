"""
api/routes/categories.py
------------------------
CRUD endpoints for rule categories.

GET    /api/rule-categories          - list categories, owner-scoped, sorted by name
POST   /api/rule-categories          - create category; 409 on duplicate name
PUT    /api/rule-categories/{id}     - rename category; 409 if new name conflicts
DELETE /api/rule-categories/{id}     - delete; sets category_id=NULL on all rules
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import RuleCategoryModel, RuleModel
from api.schemas_rule import CategoryCreateRequest, CategoryResponse, CategoryUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


def _find_category_by_name(
    owner: str, name: str, db: Session,
) -> RuleCategoryModel | None:
    """Return a category matching (owner, name) case-insensitively, or None."""
    return db.scalar(
        select(RuleCategoryModel).where(
            RuleCategoryModel.owner == owner,
            func.lower(RuleCategoryModel.name) == name.lower(),
        )
    )


def _get_owned_category(category_id: str, owner: str, db: Session) -> RuleCategoryModel:
    """Return category or raise 404 if not found / not owned."""
    cat = db.get(RuleCategoryModel, category_id)
    if cat is None or cat.owner != owner:
        logger.warning("Rule category not found: %s", category_id)
        raise HTTPException(status_code=404, detail="Category not found")
    return cat


@router.get("/rule-categories", response_model=list[CategoryResponse])
def list_categories(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RuleCategoryModel]:
    """Return all rule categories for the current user, sorted by name."""
    stmt = (
        select(RuleCategoryModel)
        .where(RuleCategoryModel.owner == current_user)
        .order_by(RuleCategoryModel.name)
    )
    return list(db.scalars(stmt).all())


@router.post("/rule-categories", response_model=CategoryResponse, status_code=201)
def create_category(
    req: CategoryCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RuleCategoryModel:
    """Create a rule category; 409 if the name already exists (case-insensitive)."""
    if _find_category_by_name(current_user, req.name, db) is not None:
        logger.warning("Duplicate rule category for user %s: %s", current_user, req.name)
        raise HTTPException(status_code=409, detail="Category name already exists")

    now = datetime.now(timezone.utc)
    cat = RuleCategoryModel(
        id=str(uuid.uuid4()),
        owner=current_user,
        name=req.name,
        created_at=now,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    logger.info("Rule category created: %s for user %s", cat.id, current_user)
    return cat


@router.put("/rule-categories/{category_id}", response_model=CategoryResponse)
def rename_category(
    category_id: str,
    req: CategoryUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RuleCategoryModel:
    """Rename a rule category; 409 if the new name conflicts with an existing one."""
    cat = _get_owned_category(category_id, current_user, db)

    conflict = _find_category_by_name(current_user, req.name, db)
    if conflict is not None and conflict.id != category_id:
        logger.warning("Rename conflict for category %s -> %s", category_id, req.name)
        raise HTTPException(status_code=409, detail="Category name already exists")

    cat.name = req.name
    db.commit()
    db.refresh(cat)
    logger.info("Rule category renamed: %s -> %s", category_id, req.name)
    return cat


@router.delete("/rule-categories/{category_id}", status_code=204)
def delete_category(
    category_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a rule category; sets category_id=NULL on all rules that used it."""
    _get_owned_category(category_id, current_user, db)

    db.execute(
        update(RuleModel)
        .where(RuleModel.category_id == category_id)
        .values(category_id=None)
    )
    cat = db.get(RuleCategoryModel, category_id)
    if cat is not None:
        db.delete(cat)
    db.commit()
    logger.info("Rule category deleted: %s", category_id)
