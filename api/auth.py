"""
api/auth.py
-----------
JWT-based authentication for the dashboard.

Users are stored in the `users` DB table (seeded from AUTH_USERS env var).
Provides a login endpoint and reusable FastAPI dependencies for
protecting routes and requiring admin privileges.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

_JWT_ALGORITHM = "HS256"
_TOKEN_EXPIRE_HOURS = 168  # 7 days

_bearer_scheme = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------

_LOGIN_RATE_LIMIT = 5
_LOGIN_RATE_WINDOW_SECONDS = 60
_login_attempts: dict[str, list[float]] = {}


def reset_login_rate_limits() -> None:
    """Clear all stored rate-limit data. Intended for test teardown only."""
    _login_attempts.clear()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    username: str
    is_admin: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_jwt_secret() -> str:
    """Read JWT_SECRET from env on each call (avoids stale module-level value)."""
    return os.getenv("JWT_SECRET", "")


def _check_login_rate_limit(request: Request) -> None:
    """Raise 429 if the IP exceeds the login attempt limit."""
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    cutoff = now - _LOGIN_RATE_WINDOW_SECONDS

    # Clean old entries for this IP
    timestamps = _login_attempts.get(ip, [])
    timestamps = [t for t in timestamps if t > cutoff]
    _login_attempts[ip] = timestamps

    if len(timestamps) >= _LOGIN_RATE_LIMIT:
        logger.warning("Rate limit exceeded for IP %s", ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )

    timestamps.append(now)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def _create_access_token(subject: str) -> str:
    """Create a signed JWT with an expiry claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRE_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, _get_jwt_secret(), algorithm=_JWT_ALGORITHM)


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
    db: Annotated[Session, Depends(get_db)],
) -> str:
    """Validate the Bearer token and return the username.

    Raises 401 if the token is missing, expired, invalid, or the user
    no longer exists in the database.
    """
    secret = _get_jwt_secret()
    if not secret:
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
            credentials.credentials, secret, algorithms=[_JWT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify the user still exists in the database
    user_exists = db.scalar(
        select(UserModel).where(UserModel.username == username),
    )
    if user_exists is None:
        logger.warning("Token valid but user %r not found in DB", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


# ---------------------------------------------------------------------------
# Login endpoint
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """Authenticate with username + password, return a JWT."""
    _check_login_rate_limit(request)
    user = db.scalar(select(UserModel).where(UserModel.username == req.username))
    if user is None:
        # Dummy verify to prevent timing side-channel (don't reveal if username exists)
        _verify_password("dummy", "$2b$12$67SobfGqs9AUtJnVdZqt6uJu/YD7Qz2JaMu3dmIkJu64ePi/3n1bS")
        logger.warning("Login failed: unknown user %r", req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not _verify_password(req.password, user.password_hash):
        logger.warning("Login failed: bad password for %r", req.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = _create_access_token(subject=req.username)
    logger.info("Login succeeded for %r", req.username)
    return LoginResponse(access_token=token)


# ---------------------------------------------------------------------------
# GET /me — current user profile
# ---------------------------------------------------------------------------


@router.get("/me", response_model=MeResponse)
def me(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MeResponse:
    """Return the current user's profile."""
    user = db.scalar(select(UserModel).where(UserModel.username == current_user))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MeResponse(username=user.username, is_admin=user.is_admin)


# ---------------------------------------------------------------------------
# POST /refresh — issue a fresh token
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=LoginResponse)
def refresh_token(
    current_user: Annotated[str, Depends(get_current_user)],
) -> LoginResponse:
    """Issue a fresh JWT if the current token is still valid."""
    token = _create_access_token(subject=current_user)
    logger.info("Token refreshed for %r", current_user)
    return LoginResponse(access_token=token)


# ---------------------------------------------------------------------------
# PUT /password — change password
# ---------------------------------------------------------------------------


@router.put("/password", response_model=MessageResponse)
def change_password(
    req: ChangePasswordRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    """Change the current user's password. Requires the current password."""
    user = db.scalar(select(UserModel).where(UserModel.username == current_user))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not _verify_password(req.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    user.password_hash = bcrypt.hash(req.new_password)
    db.commit()
    logger.info("Password changed for %r", current_user)
    return MessageResponse(message="Password updated")


# ---------------------------------------------------------------------------
# Admin dependency
# ---------------------------------------------------------------------------


def require_admin(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> str:
    """Require the current user to have admin privileges. Returns username."""
    user = db.scalar(select(UserModel).where(UserModel.username == current_user))
    if user is None or not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
