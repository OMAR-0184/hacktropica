"""
Redis-backed concurrency and idempotency primitives.

Provides distributed locking to prevent concurrent mutations on the same
session, and an idempotency cache so duplicate continue-requests return
the original response instead of re-executing.

Idempotency can fall back to a process-local cache; progression locks fail closed
when Redis is unavailable because a local lock cannot protect multiple API workers.
"""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from fastapi import HTTPException, status

from api.config import get_api_settings
from api.redis import get_redis

# ── In-process fallback stores (used when Redis is down) ──────
_LOCAL_IDEMPOTENCY: dict[str, tuple[float, dict[str, Any]]] = {}


# ── Distributed lock ──────────────────────────────────────────


async def acquire_progression_lock(session_id: str) -> tuple[bool, str]:
    """Try to acquire an exclusive lock for session progression."""
    settings = get_api_settings()
    lock_key = f"journey:lock:{session_id}"
    ttl = max(1, int(settings.journey_orchestrator_lock_ttl_seconds))
    token = secrets.token_urlsafe(24)
    redis = get_redis()
    try:
        acquired = await redis.set(lock_key, token, ex=ttl, nx=True)
        if acquired:
            return True, f"{lock_key}|{token}"
    except Exception as exc:
        # A local lock cannot protect writes across API processes. Fail closed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Progression locking is unavailable.",
        ) from exc
    return False, ""


async def release_progression_lock(lock_key: str) -> None:
    """Release a previously acquired progression lock."""
    if "|" not in lock_key:
        return
    key, token = lock_key.rsplit("|", 1)
    redis = get_redis()
    try:
        await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            key,
            token,
        )
    except Exception:
        return


# ── Idempotency cache ────────────────────────────────────────


async def idempotency_get(session_id: str, request_id: str) -> dict[str, Any] | None:
    """Retrieve a cached response for a previous request, if it exists."""
    key = f"journey:idemp:{session_id}:{request_id}"
    redis = get_redis()
    try:
        raw = await redis.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        item = _LOCAL_IDEMPOTENCY.get(key)
        if not item:
            return None
        expires_at, payload = item
        if expires_at < time.time():
            _LOCAL_IDEMPOTENCY.pop(key, None)
            return None
        return payload


async def idempotency_set(
    session_id: str, request_id: str, payload: dict[str, Any]
) -> None:
    """Cache a response so duplicate requests can be short-circuited."""
    settings = get_api_settings()
    key = f"journey:idemp:{session_id}:{request_id}"
    ttl = max(1, int(settings.journey_orchestrator_idempotency_ttl_seconds))
    redis = get_redis()
    try:
        await redis.set(key, json.dumps(payload), ex=ttl)
    except Exception:
        _LOCAL_IDEMPOTENCY[key] = (time.time() + ttl, payload)
