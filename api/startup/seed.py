"""
api/startup/seed.py
--------------------
Database seeding functions run at startup.

Seeds users from AUTH_USERS / AUTH_USERNAME env vars and creates default
accounts for any user that has none. Both functions are idempotent.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from api.models import AccountModel, UserModel

logger = logging.getLogger(__name__)


def seed_users_from_env(db: Session) -> str:
    """Import AUTH_USERS env var into the users table on first boot. Idempotent.

    Returns the first username found in env vars, or "admin" as fallback.
    """
    raw = os.getenv("AUTH_USERS", "")
    if not raw:
        username = os.getenv("AUTH_USERNAME", "")
        pw_hash = os.getenv("AUTH_PASSWORD_HASH", "")
        env_users: dict[str, str] = {username: pw_hash} if username and pw_hash else {}
    else:
        try:
            env_users = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("AUTH_USERS env var is malformed JSON — skipping user seed")
            return "admin"

    if not env_users:
        logger.warning("No users found in AUTH_USERS or AUTH_USERNAME — no users seeded")
        return "admin"

    first_username = next(iter(env_users))
    now = datetime.now(timezone.utc)
    for uname, pw_hash in env_users.items():
        existing = db.scalar(select(UserModel).where(UserModel.username == uname))
        if existing is None:
            db.add(UserModel(
                id=str(uuid.uuid4()),
                username=uname,
                password_hash=pw_hash,
                is_admin=True,
                created_at=now,
            ))
            logger.info("Seeded user %r from env var", uname)
        elif existing.password_hash != pw_hash:
            existing.password_hash = pw_hash
            logger.info("Updated password hash for user %r", uname)
    db.commit()
    return first_username


def seed_default_accounts(db: Session) -> None:
    """Create default accounts for each user that has none."""
    users = db.scalars(select(UserModel)).all()
    now = datetime.now(timezone.utc)
    defaults = [
        ("Demo", "demo", "forex"),
        ("Live", "live", "forex"),
        ("Demo", "demo", "futures_mnq"),
        ("Live", "live", "futures_mnq"),
    ]
    for user in users:
        user_count = db.scalar(
            select(func.count())
            .select_from(AccountModel)
            .where(AccountModel.owner == user.username),
        )
        if user_count is not None and user_count > 0:
            continue
        for name, acct_type, inst_type in defaults:
            db.add(AccountModel(
                id=str(uuid.uuid4()),
                name=name,
                account_type=acct_type,
                instrument_type=inst_type,
                status="active",
                prop_firm=None,
                phase=None,
                owner=user.username,
                created_at=now,
            ))
        logger.info("Seeded default accounts for user %r", user.username)
    db.commit()
