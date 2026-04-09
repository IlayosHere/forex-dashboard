"""
api/routes/accounts.py
----------------------
CRUD endpoints for trading accounts.

POST   /api/accounts              — create a new account
GET    /api/accounts               — list accounts with optional filters
PUT    /api/accounts/{account_id}  — update account (partial)
DELETE /api/accounts/{account_id}  — delete account (if no linked trades)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import AccountModel, TradeModel
from api.schemas import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def create_account(
    req: AccountCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountModel:
    """Create a new trading account."""
    now = datetime.now(timezone.utc)
    account = AccountModel(
        id=str(uuid.uuid4()),
        name=req.name,
        account_type=req.account_type,
        instrument_type=req.instrument_type,
        status=req.status,
        prop_firm=req.prop_firm,
        phase=req.phase,
        balance=req.balance,
        owner=current_user,
        created_at=now,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    logger.info("Account created: %s (%s)", account.id, account.name)
    return account


@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    instrument_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    account_type: str | None = Query(default=None),
) -> list[AccountModel]:
    """List accounts with optional filters."""
    stmt = select(AccountModel).order_by(AccountModel.created_at.asc())
    stmt = stmt.where(AccountModel.owner == current_user)
    if instrument_type is not None:
        stmt = stmt.where(AccountModel.instrument_type == instrument_type)
    if status is not None:
        stmt = stmt.where(AccountModel.status == status)
    if account_type is not None:
        stmt = stmt.where(AccountModel.account_type == account_type)
    return list(db.scalars(stmt).all())


@router.put("/accounts/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: str,
    req: AccountUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountModel:
    """Update an account (partial), return 404 if not found or not owned by current user."""
    account = db.get(AccountModel, account_id)
    if account is None or account.owner != current_user:
        logger.warning("Account not found: %s", account_id)
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = req.model_dump(exclude_unset=True)
    _ALLOWED_UPDATE_FIELDS = {"name", "status", "prop_firm", "phase", "balance"}
    for field, value in update_data.items():
        if field not in _ALLOWED_UPDATE_FIELDS:
            continue
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(
    account_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an account, return 404/409 if not found or has linked trades."""
    account = db.get(AccountModel, account_id)
    if account is None or account.owner != current_user:
        logger.warning("Account not found for deletion: %s", account_id)
        raise HTTPException(status_code=404, detail="Account not found")

    linked_trade = db.scalar(
        select(TradeModel.id).where(TradeModel.account_id == account_id).limit(1),
    )
    if linked_trade is not None:
        logger.warning("Cannot delete account %s: has linked trades", account_id)
        raise HTTPException(
            status_code=409,
            detail="Cannot delete account with linked trades",
        )

    db.delete(account)
    db.commit()
    logger.info("Account deleted: %s", account_id)
