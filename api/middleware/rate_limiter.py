"""
Redis-backed per-user sliding-window rate limiter.

Applied as FastAPI middleware to protect write endpoints from abuse.
Falls back to allowing all requests if Redis is unavailable.
"""

from __future__ import annotations

import logging
import time

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import get_api_settings
from api.redis import get_redis

logger = logging.getLogger(__name__)

# Endpoints that are rate-limited (mutating / expensive operations)
_RATE_LIMITED_PATHS: set[str] = {
    "/learning/start",
    "/learning/search",
}

# Patterns for dynamic path segments — matched by prefix + suffix
_RATE_LIMITED_PATTERNS: list[tuple[str, str]] = [
    ("/learning/", "/continue"),
    ("/learning/", "/evaluate"),
    ("/learning/", "/next"),
    ("/learning/", "/nodes"),
]


def _is_rate_limited_path(path: str) -> bool:
    """Check whether the request path should be rate-limited."""
    if path in _RATE_LIMITED_PATHS:
        return True
    for prefix, suffix in _RATE_LIMITED_PATTERNS:
        if path.startswith(prefix) and path.endswith(suffix):
            return True
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter keyed by user JWT subject."""

    async def dispatch(self, request: Request, call_next):
        # Only rate-limit write methods on specific paths
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)

        if not _is_rate_limited_path(request.url.path):
            return await call_next(request)

        # Extract user identity from the Authorization header
        user_key = _extract_user_key(request)
        if not user_key:
            # No auth header — let the auth middleware handle rejection
            return await call_next(request)

        settings = get_api_settings()
        limit = settings.rate_limit_requests_per_minute
        window = 60  # seconds

        redis = get_redis()
        redis_key = f"ratelimit:{user_key}"

        try:
            now = time.time()
            pipe = redis.pipeline()
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, now - window)
            # Count remaining entries in window
            pipe.zcard(redis_key)
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            # Set expiry on the key
            pipe.expire(redis_key, window + 1)
            results = await pipe.execute()

            request_count = results[1]
            if request_count >= limit:
                logger.warning(
                    "Rate limit exceeded for user %s on %s (%d/%d)",
                    user_key,
                    request.url.path,
                    request_count,
                    limit,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many requests. Limit is {limit} per minute.",
                            "status": 429,
                        }
                    },
                    headers={"Retry-After": str(window)},
                )
        except Exception:
            # Redis down — allow the request through
            logger.debug("Rate limiter Redis unavailable, allowing request through")

        return await call_next(request)


def _extract_user_key(request: Request) -> str | None:
    """Extract a rate-limiting key from the Authorization header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    # Use last 16 chars of token as key (avoids storing full JWT in Redis)
    return token[-16:] if len(token) >= 16 else token
