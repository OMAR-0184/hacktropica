"""Async Redis task queue producer powered by arq."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool

from api.config import get_api_settings

logger = logging.getLogger(__name__)

QUEUE_NAME = "cognimap-learning"
ALLOWED_JOBS = {
    "start_learning_task",
    "resume_learning_task",
    "advance_learning_task",
}


class TaskQueueClient:
    """Application wrapper around arq's native Python async Redis queue."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool: ArqRedis | None = None
        self._queue_name = QUEUE_NAME

    async def _get_pool(self) -> ArqRedis:
        if self._pool is None:
            settings = RedisSettings.from_dsn(self._redis_url)
            self._pool = await create_pool(settings)
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None

    async def ping(self) -> bool:
        pool = await self._get_pool()
        return bool(await pool.ping())

    async def enqueue_job(
        self, name: str, *args: Any, job_id: str | None = None
    ) -> str:
        if name not in ALLOWED_JOBS:
            raise ValueError(f"Unsupported learning job: {name}")

        if job_id is None:
            stable_key = json.dumps(
                [name, args], sort_keys=True, separators=(",", ":"), default=str
            )
        else:
            stable_key = str(job_id)
        arq_job_id = f"{name}-{hashlib.sha256(stable_key.encode()).hexdigest()[:40]}"

        pool = await self._get_pool()
        job = await pool.enqueue_job(
            name,
            *args,
            _job_id=arq_job_id,
            _queue_name=self._queue_name,
        )
        if job is not None:
            return str(job.job_id)
        return arq_job_id


# Compatibility alias
BullMQClient = TaskQueueClient

_queue_client: TaskQueueClient | None = None


def start_queue_client() -> TaskQueueClient:
    global _queue_client
    _queue_client = TaskQueueClient(get_api_settings().redis_url)
    return _queue_client


def get_queue_client() -> TaskQueueClient:
    if _queue_client is None:
        raise RuntimeError("Task queue client has not been initialized")
    return _queue_client


async def close_queue_client() -> None:
    global _queue_client
    if _queue_client is not None:
        await _queue_client.close()
        _queue_client = None
