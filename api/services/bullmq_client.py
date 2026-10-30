"""BullMQ producer used by API processes."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from bullmq import Queue

from api.config import get_api_settings

QUEUE_NAME = "cognimap-learning"
ALLOWED_JOBS = {
    "start_learning_task",
    "resume_learning_task",
    "advance_learning_task",
}


class BullMQClient:
    """Small application wrapper around BullMQ's native Python queue."""

    def __init__(self, redis_url: str) -> None:
        self._queue = Queue(QUEUE_NAME, {"connection": redis_url})

    async def close(self) -> None:
        await self._queue.close()

    async def ping(self) -> bool:
        return bool(await self._queue.client.ping())

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
        bull_job_id = f"{name}-{hashlib.sha256(stable_key.encode()).hexdigest()[:40]}"

        existing = await self._queue.getJob(bull_job_id)
        if existing is not None:
            state = await existing.getState()
            if state == "failed":
                await existing.retry("failed")
            return str(existing.id)

        job = await self._queue.add(
            name,
            {"args": list(args)},
            {
                "jobId": bull_job_id,
                "attempts": 3,
                "backoff": {"type": "exponential", "delay": 1_000},
                "removeOnComplete": {"age": 3_600, "count": 1_000},
                "removeOnFail": {"age": 86_400, "count": 5_000},
            },
        )
        return str(job.id)


_queue_client: BullMQClient | None = None


def start_queue_client() -> BullMQClient:
    global _queue_client
    _queue_client = BullMQClient(get_api_settings().redis_url)
    return _queue_client


def get_queue_client() -> BullMQClient:
    if _queue_client is None:
        raise RuntimeError("BullMQ client has not been initialized")
    return _queue_client


async def close_queue_client() -> None:
    global _queue_client
    if _queue_client is not None:
        await _queue_client.close()
        _queue_client = None
