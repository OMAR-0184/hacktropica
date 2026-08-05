
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
    return Redis(connection_pool=_ensure_pool())


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
