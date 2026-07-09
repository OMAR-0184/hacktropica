"""
Shared Redis connection pool — single pool for the entire process.

Every module that needs Redis (concurrency, pub/sub, runner, websocket)
should call ``get_redis()`` instead of creating its own connection.
The pool is lazily initialized on first use and closed via
``close_redis_pool()`` during application shutdown.
"""

from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from api.config import get_api_settings

_pool: ConnectionPool | None = None


def _ensure_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_api_settings()
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=False,
        )
    return _pool


def get_redis() -> Redis:
    """Return a Redis client backed by the shared connection pool."""
    return Redis(connection_pool=_ensure_pool())


async def close_redis_pool() -> None:
    """Drain the pool on application shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
