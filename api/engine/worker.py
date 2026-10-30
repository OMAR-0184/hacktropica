"""BullMQ worker process for learning graph jobs."""

from __future__ import annotations

import asyncio
import logging
import secrets
import signal
from collections.abc import Awaitable, Callable
from typing import Any

from bullmq import Worker

from api.config import get_api_settings
from api.engine.runner import (
    advance_graph_stream,
    resume_graph_stream,
    run_learning_graph,
    runtime,
)
from api.redis import close_redis_pool, get_redis
from api.services.bullmq_client import ALLOWED_JOBS, QUEUE_NAME

logger = logging.getLogger("cognimap.worker")
LOCK_TTL_MS = 660_000
LOCK_RENEW_INTERVAL_SECONDS = 60


async def _renew_session_lock(key: str, token: str) -> None:
    redis = get_redis()
    while True:
        await asyncio.sleep(LOCK_RENEW_INTERVAL_SECONDS)
        renewed = await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('pexpire', KEYS[1], ARGV[2]) else return 0 end",
            1,
            key,
            token,
            LOCK_TTL_MS,
        )
        if not renewed:
            raise RuntimeError("Learning session worker lock expired")


async def _run_session_serially(
    session_id: str, operation: Callable[[], Awaitable[bool]]
) -> bool:
    """Serialize graph writes for a session across worker processes."""
    redis = get_redis()
    key = f"bullmq:session-lock:{session_id}"
    token = secrets.token_urlsafe(24)
    while not await redis.set(key, token, nx=True, px=LOCK_TTL_MS):
        await asyncio.sleep(0.25)

    renewer = asyncio.create_task(_renew_session_lock(key, token))
    operation_task: asyncio.Task[bool] | None = None
    try:
        operation_task = asyncio.create_task(operation())
        done, _ = await asyncio.wait(
            {operation_task, renewer}, return_when=asyncio.FIRST_COMPLETED
        )
        if renewer in done:
            await renewer
        result = await operation_task
        if not result:
            raise RuntimeError("Learning graph task returned failure")
        return result
    finally:
        if operation_task is not None and not operation_task.done():
            operation_task.cancel()
            await asyncio.gather(operation_task, return_exceptions=True)
        renewer.cancel()
        await asyncio.gather(renewer, return_exceptions=True)
        await redis.eval(
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end",
            1,
            key,
            token,
        )


async def process_job(job: Any, _job_token: str) -> dict[str, str]:
    if job.name not in ALLOWED_JOBS:
        raise ValueError(f"Unknown learning job: {job.name}")

    args = job.data.get("args") if isinstance(job.data, dict) else None
    if not isinstance(args, list) or not args or not args[0]:
        raise ValueError("Learning job must include a session id")
    session_id = str(args[0])

    if job.name == "start_learning_task" and 3 <= len(args) <= 6:
        _, topic, course_mode, *rest = args
        traversal_mode = "dfs"
        learner_profile = ""
        journey_v2 = False
        if len(rest) == 2:
            learner_profile, journey_v2 = rest
        elif len(rest) >= 3:
            traversal_mode, learner_profile, journey_v2 = rest[:3]

        operation = lambda: run_learning_graph(
            session_id=session_id,
            topic=str(topic),
            course_mode=str(course_mode),
            traversal_mode=str(traversal_mode),
            learner_profile=str(learner_profile or ""),
            journey_orchestrator_v2=bool(journey_v2),
        )
    elif job.name == "resume_learning_task" and len(args) == 2:
        operation = lambda: resume_graph_stream(session_id, args[1])
    elif job.name == "advance_learning_task" and len(args) == 1:
        operation = lambda: advance_graph_stream(session_id)
    else:
        raise ValueError("Invalid arguments for learning job")

    await _run_session_serially(session_id, operation)
    return {"status": "completed"}


async def main() -> None:
    settings = get_api_settings()
    settings.validate_runtime()
    await runtime.start()

    shutdown = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown.set)

    worker = Worker(
        QUEUE_NAME,
        process_job,
        {
            "connection": settings.redis_url,
            "concurrency": 10,
            "lockDuration": LOCK_TTL_MS,
            "lockRenewTime": LOCK_TTL_MS // 2,
        },
    )
    worker.on(
        "failed",
        lambda job, error: logger.error(
            "BullMQ job failed id=%s name=%s error=%s",
            getattr(job, "id", None),
            getattr(job, "name", None),
            error,
        ),
    )
    worker.on("error", lambda error, *_: logger.exception("BullMQ worker error: %s", error))

    logger.info("BullMQ worker started queue=%s", QUEUE_NAME)
    try:
        await shutdown.wait()
    finally:
        await worker.close()
        await runtime.stop()
        await close_redis_pool()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
