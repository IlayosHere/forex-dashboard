"""
api/life_lock.py
-----------------
Second-factor passphrase gate for the /life journal routes.

Sits on top of the existing JWT auth (api/auth.py): a user must already hold
a valid main-app token to call POST /life/unlock, and the resulting unlock
token only ever grants access to the /life/* routes, never the rest of the
API. Failures here always return 403, never 401 — a wrong passphrase must
not log the user out of the whole app (the frontend's fetch wrapper treats
401 as "main session expired").
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, Field

from api.auth import get_current_user
from api.auth_rate_limit import check_life_unlock_rate_limit
from api.auth_rate_limit import reset_life_unlock_rate_limits as reset_life_unlock_rate_limits  # re-exported

logger = logging.getLogger(__name__)

router = APIRouter()

_ALGORITHM = "HS256"
_LIFE_SCOPE = "life"
_UNLOCK_EXPIRE_HOURS: int = int(os.getenv("LIFE_UNLOCK_EXPIRE_HOURS", "12"))


class LifeUnlockRequest(BaseModel):
    passphrase: str = Field(..., min_length=1, max_length=128)


class LifeUnlockResponse(BaseModel):
    unlock_token: str
    expires_in_hours: int


def _get_jwt_secret() -> str:
    """Read JWT_SECRET from env on each call (avoids stale module-level value)."""
    return os.getenv("JWT_SECRET", "")


def _get_life_password_hash() -> str:
    """Read LIFE_PASSWORD_HASH from env on each call (avoids stale module-level value)."""
    return os.getenv("LIFE_PASSWORD_HASH", "")


def _create_unlock_token(subject: str) -> str:
    """Create a signed JWT scoped to the life journal, distinct from the main app token."""
    expire = datetime.now(timezone.utc) + timedelta(hours=_UNLOCK_EXPIRE_HOURS)
    payload = {"sub": subject, "scope": _LIFE_SCOPE, "exp": expire}
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_ALGORITHM)


@router.post("/life/unlock", response_model=LifeUnlockResponse)
def unlock_life(
    req: LifeUnlockRequest,
    request: Request,
    current_user: Annotated[str, Depends(get_current_user)],
) -> LifeUnlockResponse:
    """Verify the life-journal passphrase and issue a scoped unlock token."""
    check_life_unlock_rate_limit(request)
    password_hash = _get_life_password_hash()
    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LIFE_PASSWORD_HASH is not configured",
        )
    if not bcrypt.verify(req.passphrase, password_hash):
        logger.warning("Life unlock failed for user %r", current_user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid passphrase")
    logger.info("Life journal unlocked for %r", current_user)
    return LifeUnlockResponse(
        unlock_token=_create_unlock_token(current_user),
        expires_in_hours=_UNLOCK_EXPIRE_HOURS,
    )


def require_life_unlock(
    current_user: Annotated[str, Depends(get_current_user)],
    x_life_unlock: Annotated[str | None, Header()] = None,
) -> str:
    """Validate the X-Life-Unlock header, scoped and bound to the current user.

    Raises 403 (not 401) on any failure, including missing configuration —
    fails closed rather than treating an unset passphrase as "unlocked".
    """
    secret = _get_jwt_secret()
    password_hash = _get_life_password_hash()
    if not secret or not password_hash:
        logger.error("Life lock misconfigured: JWT_SECRET or LIFE_PASSWORD_HASH unset")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Life journal is locked")
    if x_life_unlock is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Life journal is locked")
    try:
        payload = jwt.decode(x_life_unlock, secret, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Life journal is locked")
    if payload.get("scope") != _LIFE_SCOPE or payload.get("sub") != current_user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Life journal is locked")
    return current_user
