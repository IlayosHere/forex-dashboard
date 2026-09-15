"""
api/auth_rate_limit.py
-----------------------
In-memory per-IP rate limiting for login attempts.

Intentionally simple: uses a dict of timestamps per IP. Not suitable for
multi-process deployments — for single-process uvicorn this is sufficient.
"""
from __future__ import annotations

import logging
import threading
import time

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

_LOGIN_RATE_LIMIT: int = 5
_LOGIN_RATE_WINDOW_SECONDS: int = 60
_login_attempts: dict[str, list[float]] = {}

_LIFE_UNLOCK_RATE_LIMIT: int = 5
_LIFE_UNLOCK_RATE_WINDOW_SECONDS: int = 60
_life_unlock_attempts: dict[str, list[float]] = {}

_lock = threading.Lock()


def _cleanup_stale_ips(attempts: dict[str, list[float]]) -> None:
    """Remove IPs whose timestamp lists are empty. Caller must hold _lock."""
    stale = [ip for ip, ts in attempts.items() if not ts]
    for ip in stale:
        del attempts[ip]


def reset_login_rate_limits() -> None:
    """Clear all stored login rate-limit data. Intended for test teardown only."""
    with _lock:
        _login_attempts.clear()
        _cleanup_stale_ips(_login_attempts)


def reset_life_unlock_rate_limits() -> None:
    """Clear all stored life-unlock rate-limit data. Intended for test teardown only."""
    with _lock:
        _life_unlock_attempts.clear()
        _cleanup_stale_ips(_life_unlock_attempts)


def _get_client_ip(request: Request) -> str:
    """Extract the client IP from the request, preferring X-Forwarded-For.

    Note: X-Forwarded-For can be spoofed unless the upstream proxy strips it.
    For a private tool behind a trusted nginx proxy this is acceptable.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check_bucket(
    request: Request,
    attempts: dict[str, list[float]],
    limit: int,
    window_seconds: int,
    label: str,
) -> None:
    """Raise 429 if the requesting IP exceeds `limit` attempts within `window_seconds`."""
    ip = _get_client_ip(request)
    now = time.monotonic()
    cutoff = now - window_seconds

    with _lock:
        timestamps = [t for t in attempts.get(ip, []) if t > cutoff]
        timestamps.append(now)
        attempts[ip] = timestamps

        if len(timestamps) >= limit:
            logger.warning("Rate limit exceeded for IP %s (%s)", ip, label)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Try again later.",
            )


def check_login_rate_limit(request: Request) -> None:
    """Raise 429 if the requesting IP exceeds the login attempt limit."""
    _check_bucket(
        request, _login_attempts, _LOGIN_RATE_LIMIT, _LOGIN_RATE_WINDOW_SECONDS, "login",
    )


def check_life_unlock_rate_limit(request: Request) -> None:
    """Raise 429 if the requesting IP exceeds the life-unlock attempt limit."""
    _check_bucket(
        request,
        _life_unlock_attempts,
        _LIFE_UNLOCK_RATE_LIMIT,
        _LIFE_UNLOCK_RATE_WINDOW_SECONDS,
        "life-unlock",
    )
