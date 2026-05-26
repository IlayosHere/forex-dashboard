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

    AUTH_USERS format (JSON dict):
        {"username": "pw_hash"}                  — admin=True (backwards compatible)
        {"username": "pw_hash:true"}             — admin=True
        {"username": "pw_hash:false"}            — admin=False (non-admin user)

    The optional third colon-delimited field on the value controls is_admin.
    If absent, defaults to True for backwards compatibility.

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
    for uname, raw_value in env_users.items():
        parts = raw_value.split(":", 1)
        pw_hash = parts[0]
        is_admin = parts[1].strip().lower() != "false" if len(parts) > 1 else True
        existing = db.scalar(select(UserModel).where(UserModel.username == uname))
        if existing is None:
            db.add(UserModel(
                id=str(uuid.uuid4()),
                username=uname,
                password_hash=pw_hash,
                is_admin=is_admin,
                created_at=now,
            ))
            logger.info("Seeded user %r (is_admin=%s) from env var", uname, is_admin)
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
        ("Demo", "demo", "futures"),
        ("Live", "live", "futures"),
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
