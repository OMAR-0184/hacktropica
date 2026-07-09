"""
Redis-backed concurrency and idempotency primitives.

Provides distributed locking to prevent concurrent mutations on the same
session, and an idempotency cache so duplicate continue-requests return
the original response instead of re-executing.

Falls back to in-process dicts when Redis is unreachable.
"""

from __future__ import annotations

import json
import time
from typing import Any

from api.config import get_api_settings
from api.redis import get_redis

# ── In-process fallback stores (used when Redis is down) ──────
_LOCAL_LOCKS: dict[str, float] = {}
_LOCAL_IDEMPOTENCY: dict[str, tuple[float, dict[str, Any]]] = {}


# ── Distributed lock ──────────────────────────────────────────


async def acquire_progression_lock(session_id: str) -> tuple[bool, str]:
    """Try to acquire an exclusive lock for session progression."""
    settings = get_api_settings()
    lock_key = f"journey:lock:{session_id}"
    ttl = max(1, int(settings.journey_orchestrator_lock_ttl_seconds))
    redis = get_redis()
    try:
        acquired = await redis.set(lock_key, "1", ex=ttl, nx=True)
        if acquired:
            return True, lock_key
    except Exception:
        # Redis unavailable — fall back to in-process lock
        now = time.time()
        if _LOCAL_LOCKS.get(lock_key, 0.0) <= now:
            _LOCAL_LOCKS[lock_key] = now + ttl
            return True, lock_key
        return False, lock_key
    return False, lock_key


async def release_progression_lock(lock_key: str) -> None:
    """Release a previously acquired progression lock."""
    redis = get_redis()
    try:
        await redis.delete(lock_key)
    except Exception:
        _LOCAL_LOCKS.pop(lock_key, None)


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
