"""
api/auth.py
-----------
JWT-based authentication for the dashboard.

Multi-user auth via environment variables — no user database table.
Users are defined in the AUTH_USERS env var as a JSON object mapping
usernames to bcrypt password hashes.
Provides a login endpoint and a reusable FastAPI dependency for
protecting routes.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

_JWT_SECRET = os.getenv("JWT_SECRET", "")
_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 24

# Multi-user: AUTH_USERS is a JSON object {"username": "bcrypt_hash", ...}
# Falls back to legacy single-user AUTH_USERNAME + AUTH_PASSWORD_HASH if set.
def _load_users() -> dict[str, str]:
    raw = os.getenv("AUTH_USERS", "")
    if raw:
        return json.loads(raw)
    # Legacy single-user fallback
    username = os.getenv("AUTH_USERNAME", "admin")
    pw_hash = os.getenv("AUTH_PASSWORD_HASH", "")
    if pw_hash:
        return {username: pw_hash}
    return {}

_AUTH_USERS: dict[str, str] = _load_users()

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _create_access_token(subject: str) -> str:
    """Create a signed JWT with an expiry claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    if not hashed:
        return False
    return bcrypt.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Dependency — inject into any route that needs auth
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> str:
    """Validate the Bearer token and return the username.

    Raises 401 if the token is missing, expired, or invalid.
    """
    if not _JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials, _JWT_SECRET, algorithms=[_JWT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest) -> LoginResponse:
    """Authenticate with username + password, return a JWT."""
    pw_hash = _AUTH_USERS.get(req.username)
    if pw_hash is None:
        logger.warning("Login failed: unknown user %r", req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not _verify_password(req.password, pw_hash):
        logger.warning("Login failed: bad password for %r", req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = _create_access_token(subject=req.username)
    logger.info("Login succeeded for %r", req.username)
    return LoginResponse(access_token=token)
