"""
arq Worker Configuration

This module acts as the ARQ worker entry point.
Run via: arq api.engine.worker.WorkerSettings
"""

import logging
from arq import Worker
from arq.connections import RedisSettings

from api.config import get_api_settings
from api.engine.runner import run_learning_graph, resume_graph_stream, advance_graph_stream

logger = logging.getLogger(__name__)
_settings = get_api_settings()


async def start_learning_task(
    ctx,
    session_id: str,
    topic: str,
    course_mode: str = "detailed",
    *args,
):
    """ARQ task to initialize the learning graph and begin streaming."""
    traversal_mode = "dfs"
    learner_profile = ""
    journey_orchestrator_v2 = False

    # Backward/forward compatible argument parsing:
    # old payload: [learner_profile, journey_orchestrator_v2]
    # new payload: [traversal_mode, learner_profile, journey_orchestrator_v2]
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
    
    # Parse the standard redis://host:port/... URL into RedisSettings
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)

    # Optional: You can do connection pooling for the DB here,
    # but SQLAlchemy via create_async_engine handles its own pool 
    # cleanly out of the box so long as we are in a single event loop!
