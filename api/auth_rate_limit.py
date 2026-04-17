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
_lock = threading.Lock()


def _cleanup_stale_ips() -> None:
    """Remove IPs whose timestamp lists are empty. Caller must hold _lock."""
    stale = [ip for ip, ts in _login_attempts.items() if not ts]
    for ip in stale:
        del _login_attempts[ip]


def reset_login_rate_limits() -> None:
    """Clear all stored rate-limit data. Intended for test teardown only."""
    with _lock:
        _login_attempts.clear()
        _cleanup_stale_ips()


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


def check_login_rate_limit(request: Request) -> None:
    """Raise 429 if the requesting IP exceeds the login attempt limit."""
    ip = _get_client_ip(request)
    now = time.monotonic()
    cutoff = now - _LOGIN_RATE_WINDOW_SECONDS

    with _lock:
        timestamps = [t for t in _login_attempts.get(ip, []) if t > cutoff]
        timestamps.append(now)
        _login_attempts[ip] = timestamps

        if len(timestamps) > _LOGIN_RATE_LIMIT:
            logger.warning("Rate limit exceeded for IP %s", ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
