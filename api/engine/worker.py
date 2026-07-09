"""
arq Worker Configuration

This module acts as the ARQ worker entry point.
Run via: arq api.engine.worker.WorkerSettings
"""

import logging
from arq.connections import RedisSettings

from api.config import get_api_settings
from api.engine.runner import (
    runtime,
    run_learning_graph,
    resume_graph_stream,
    advance_graph_stream,
)

logger = logging.getLogger(__name__)
_settings = get_api_settings()


async def startup(ctx: dict) -> None:
    """Initialize the GraphRuntime once per worker process."""
    logger.info("ARQ worker starting — initializing GraphRuntime…")
    await runtime.start()
    ctx["runtime_started"] = True


async def shutdown(ctx: dict) -> None:
    """Clean up the GraphRuntime on worker shutdown."""
    logger.info("ARQ worker shutting down — closing GraphRuntime…")
    await runtime.stop()


async def start_learning_task(
    ctx,
    session_id: str,
    topic: str,
    course_mode: str = "detailed",
    *args,
):
    traversal_mode = "dfs"
    learner_profile = ""
    journey_orchestrator_v2 = False
    if len(args) == 2:
        learner_profile = str(args[0] or "")
        journey_orchestrator_v2 = bool(args[1])
    elif len(args) >= 3:
        maybe_mode = str(args[0] or "").strip().lower()
        traversal_mode = maybe_mode if maybe_mode in {"bfs", "dfs"} else "dfs"
        learner_profile = str(args[1] or "")
        journey_orchestrator_v2 = bool(args[2])

    logger.info("ARQ triggering run_learning_graph for %s", session_id)
    await run_learning_graph(
        session_id=session_id,
        topic=topic,
        course_mode=course_mode,
        traversal_mode=traversal_mode,
        learner_profile=learner_profile,
        journey_orchestrator_v2=journey_orchestrator_v2,
    )


async def resume_learning_task(ctx, session_id: str, user_answers: list):
    """ARQ task to process evaluation answers and resume streaming."""
    logger.info("ARQ triggering resume_graph_stream for %s", session_id)
    await resume_graph_stream(session_id, user_answers)


async def advance_learning_task(ctx, session_id: str):
    """ARQ task to advance the graph to the next logic node."""
    logger.info("ARQ triggering advance_graph_stream for %s", session_id)
    await advance_graph_stream(session_id)


class WorkerSettings:
    functions = [
        start_learning_task,
        resume_learning_task,
        advance_learning_task,
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = RedisSettings.from_dsn(_settings.redis_url)

    # ── Scaling & reliability settings ────────────────────────
    max_jobs = 10                  # Concurrent jobs per worker process
    job_timeout = 120              # Kill stalled LLM calls after 2 min
    health_check_interval = 30     # Heartbeat interval for monitoring
