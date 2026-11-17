"""Async Redis task queue worker powered by arq."""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Any

from arq.connections import RedisSettings
from arq.worker import run_worker

from api.config import get_api_settings
from api.engine.runner import (
    advance_graph_stream,
    resume_graph_stream,
    run_learning_graph,
    runtime,
)
from api.redis import close_redis_pool, get_redis
from api.services.task_queue import QUEUE_NAME

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
    key = f"task-queue:session-lock:{session_id}"
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


async def start_learning_task(
    ctx: dict[str, Any],
    session_id: str,
    topic: str,
    course_mode: str = "detailed",
    traversal_mode: str = "dfs",
    learner_profile: str = "",
    journey_v2: bool = False,
    *args: Any,
) -> dict[str, str]:
    operation = lambda: run_learning_graph(
        session_id=str(session_id),
        topic=str(topic),
        course_mode=str(course_mode),
        traversal_mode=str(traversal_mode),
        learner_profile=str(learner_profile or ""),
        journey_orchestrator_v2=bool(journey_v2),
    )
    await _run_session_serially(str(session_id), operation)
    return {"status": "completed"}


async def resume_learning_task(
    ctx: dict[str, Any],
    session_id: str,
    user_answers: list,
    *args: Any,
) -> dict[str, str]:
    operation = lambda: resume_graph_stream(str(session_id), user_answers)
    await _run_session_serially(str(session_id), operation)
    return {"status": "completed"}


async def advance_learning_task(
    ctx: dict[str, Any],
    session_id: str,
    *args: Any,
) -> dict[str, str]:
    operation = lambda: advance_graph_stream(str(session_id))
    await _run_session_serially(str(session_id), operation)
    return {"status": "completed"}


async def process_job(job: Any, _job_token: str = "") -> dict[str, str]:
    """Compatibility dispatcher for processing job objects."""
    job_name = getattr(job, "name", "")
    data = getattr(job, "data", {})
    args = data.get("args") if isinstance(data, dict) else None
    if not isinstance(args, list) or not args:
        raise ValueError("Learning job must include arguments")

    ctx = {"job": job}
    if job_name == "start_learning_task":
        return await start_learning_task(ctx, *args)
    elif job_name == "resume_learning_task":
        return await resume_learning_task(ctx, *args)
    elif job_name == "advance_learning_task":
        return await advance_learning_task(ctx, *args)
    else:
        raise ValueError(f"Unknown learning job: {job_name}")


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_api_settings()
    settings.validate_runtime()
    await runtime.start()
    logger.info("Task queue worker started queue=%s", QUEUE_NAME)


async def shutdown(ctx: dict[str, Any]) -> None:
    await runtime.stop()
    await close_redis_pool()
    logger.info("Task queue worker stopped")


class WorkerSettings:
    functions = [start_learning_task, resume_learning_task, advance_learning_task]
    redis_settings = RedisSettings.from_dsn(get_api_settings().redis_url)
    queue_name = QUEUE_NAME
    max_jobs = 10
    on_startup = startup
    on_shutdown = shutdown
    job_timeout = 600


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
