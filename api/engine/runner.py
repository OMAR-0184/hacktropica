"""
Graph execution runtime — pooled checkpointer and cached graph.

Replaces the previous pattern of creating a new Postgres connection
and rebuilding the graph on every single API call. The ``GraphRuntime``
class is initialized once during the FastAPI lifespan and shared across
all requests.
"""

import json
import logging
import traceback
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.graph import build_graph
from api.config import get_api_settings
from api.database.core import SessionLocal
from api.database.models import Session, NodeState
from api.redis import get_redis

from sqlalchemy import select

logger = logging.getLogger(__name__)

_settings = get_api_settings()
# SQLAlchemy dialect prefixes confuse raw psycopg conninfo parsers
DB_URI = _settings.database_url_sync.replace("+psycopg", "").replace("+asyncpg", "")


# ── Singleton runtime ─────────────────────────────────────────


class GraphRuntime:
    """Holds a pooled checkpointer and a pre-compiled graph."""

    def __init__(self) -> None:
        self._checkpointer_ctx = None
        self._checkpointer: AsyncPostgresSaver | None = None
        self._graph = None

    async def start(self) -> None:
        """Open the connection pool and compile the graph once."""
        self._checkpointer_ctx = AsyncPostgresSaver.from_conn_string(DB_URI)
        self._checkpointer = await self._checkpointer_ctx.__aenter__()
        await self._checkpointer.setup()
        self._graph = build_graph(checkpointer=self._checkpointer)

    async def stop(self) -> None:
        """Drain the checkpointer pool on shutdown."""
        if self._checkpointer_ctx is not None:
            try:
                await self._checkpointer_ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self._checkpointer_ctx = None
            self._checkpointer = None
            self._graph = None

    @property
    def graph(self):
        if self._graph is None:
            raise RuntimeError("GraphRuntime not started — call start() first")
        return self._graph

    @property
    def checkpointer(self) -> AsyncPostgresSaver:
        if self._checkpointer is None:
            raise RuntimeError("GraphRuntime not started — call start() first")
        return self._checkpointer


# Module-level singleton — initialized via ``await runtime.start()``
# during the FastAPI lifespan.
runtime = GraphRuntime()


# ── Redis pub/sub ─────────────────────────────────────────────


async def _publish_to_redis(session_id: str, message: dict):
    """
    Publish a session event via the shared Redis pool.

    Works from ANY process (ARQ workers included) because it uses
    the pooled connection, not the FastAPI ConnectionManager.
    """
    redis = get_redis()
    try:
        payload = json.dumps(message)
        await redis.publish(f"session:{session_id}", payload)
    except Exception:
        logger.warning("Failed to publish Redis event for session %s", session_id)


# ── Graph streaming ───────────────────────────────────────────


async def stream_graph_events(
    session_id: str, graph, config: dict, input_data=None
) -> bool:
    try:
        async for output in graph.astream(
            input_data, config=config, stream_mode="updates"
        ):
            for node_name, partial_state in output.items():
                logger.info(f"Graph hit node: {node_name}")
                await _publish_to_redis(
                    session_id,
                    {
                        "type": "node_update",
                        "node": node_name,
                        "data": partial_state,
                    },
                )

        await sync_state_to_db(session_id, config, graph)
        await _publish_to_redis(
            session_id, {"type": "status", "message": "Completed step"}
        )
        return True
    except Exception as e:
        err_msg = str(e)
        logger.error(f"Graph execution error: {traceback.format_exc()}")
        await _update_session_status(session_id, "error", error_message=err_msg)
        await _publish_to_redis(session_id, {"type": "error", "message": err_msg})
        return False


# ── Public API (used by workers and services) ─────────────────


async def _get_graph_and_config(session_id: str):
    """Return the shared graph and a session-scoped config dict."""
    return runtime.graph, {"configurable": {"thread_id": session_id}}


async def run_learning_graph(
    session_id: str,
    topic: str,
    course_mode: str = "detailed",
    traversal_mode: str = "dfs",
    learner_profile: str = "",
    journey_orchestrator_v2: bool = False,
):
    """
    Async background runner for initializing the graph and streaming events.
    """
    await _update_session_status(session_id, "running", current_phase="root")

    graph, config = await _get_graph_and_config(session_id)
    state = {
        "topic": topic,
        "course_mode": course_mode,
        "traversal_mode": traversal_mode
        if traversal_mode in {"bfs", "dfs"}
        else "dfs",
        "learner_profile": learner_profile,
        "journey_orchestrator_v2": bool(journey_orchestrator_v2),
    }

    await _publish_to_redis(
        session_id, {"type": "status", "message": "Graph Initialized"}
    )
    success = await stream_graph_events(session_id, graph, config, state)

    if success:
        await _update_session_status(session_id, "ready", current_phase="lesson")


async def get_current_state(session_id: str):
    graph, config = await _get_graph_and_config(session_id)
    state_snapshot = await graph.aget_state(config)
    return state_snapshot


async def set_next_choice(
    session_id: str, selected_node: str | None = None, traversal_mode: str | None = None
):
    """
    Persist user journey-selection preferences in graph state before advancing.
    """
    updates: dict[str, str] = {}
    if selected_node is not None:
        updates["selected_next_node"] = selected_node
    if traversal_mode is not None:
        normalized_mode = traversal_mode.strip().lower()
        if normalized_mode in {"bfs", "dfs"}:
            updates["traversal_mode"] = normalized_mode

    if not updates:
        return

    graph, config = await _get_graph_and_config(session_id)
    await graph.aupdate_state(config, updates)


async def apply_state_updates(session_id: str, updates: dict[str, Any]) -> None:
    """
    Apply a partial state patch directly to the graph checkpoint.
    """
    if not isinstance(updates, dict) or not updates:
        return

    graph, config = await _get_graph_and_config(session_id)
    await graph.aupdate_state(config, updates)


async def sync_state_to_db(session_id: str, config: dict, graph_instance=None):
    """
    Syncs the latest state from the langgraph checkpoint to our relational schema.
    """
    if graph_instance:
        snapshot = await graph_instance.aget_state(config)
    else:
        graph, cfg = await _get_graph_and_config(session_id)
        snapshot = await graph.aget_state(cfg)

    if snapshot and snapshot.values:
        values = snapshot.values
        async with SessionLocal() as db:
            result = await db.execute(select(Session).filter(Session.id == session_id))
            db_session = result.scalars().first()
            if db_session:
                current_subtopic = values.get("current_node")
                if current_subtopic:
                    existing_result = await db.execute(
                        select(NodeState).filter(
                            NodeState.session_id == session_id,
                            NodeState.node_id == current_subtopic,
                        )
                    )
                    existing_node = existing_result.scalars().first()
                    if not existing_node:
                        new_node = NodeState(
                            session_id=session_id,
                            node_id=current_subtopic,
                            node_type="learning",
                            status="active",
                        )
                        db.add(new_node)
                await db.commit()


async def resume_graph_stream(session_id: str, user_answers: list):
    await _update_session_status(session_id, "evaluating", current_phase="evaluator")

    graph, config = await _get_graph_and_config(session_id)
    await graph.aupdate_state(
        config, {"evaluation": {"user_answers": user_answers}}
    )
    await _publish_to_redis(
        session_id, {"type": "status", "message": "Resuming after evaluation"}
    )
    success = await stream_graph_events(session_id, graph, config, None)

    if success:
        await _update_session_status(session_id, "ready", current_phase="evaluator")


async def advance_graph_stream(session_id: str):
    await _update_session_status(session_id, "running", current_phase="advancing")

    graph, config = await _get_graph_and_config(session_id)
    await _publish_to_redis(
        session_id, {"type": "status", "message": "Advancing graph"}
    )
    success = await stream_graph_events(session_id, graph, config, None)

    if success:
        snapshot = await get_current_state(session_id)
        if snapshot and snapshot.values and _is_curriculum_completed(snapshot.values):
            await _update_session_status(
                session_id, "completed", current_phase="completed"
            )
        else:
            await _update_session_status(session_id, "ready", current_phase="lesson")


async def _update_session_status(
    session_id: str,
    status: str,
    current_phase: str | None = None,
    error_message: str | None = None,
):
    """Helper to update the session status and phase in the DB."""
    async with SessionLocal() as db:
        result = await db.execute(select(Session).filter(Session.id == session_id))
        db_session = result.scalars().first()
        if db_session:
            db_session.status = status
            if current_phase is not None:
                db_session.current_phase = current_phase
            if error_message is not None:
                db_session.error_message = error_message
            await db.commit()


def _is_curriculum_completed(values: dict) -> bool:
    subtopics = values.get("subtopics", [])
    mastery = values.get("mastery", {})
    if not isinstance(subtopics, list) or not subtopics:
        return False
    if not isinstance(mastery, dict):
        return False
    return all(bool(mastery.get(st, False)) for st in subtopics)
