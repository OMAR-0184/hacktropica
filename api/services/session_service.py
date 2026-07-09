"""
Session lifecycle management.

Handles creation, lookup, listing, archival, and WebSocket access checks.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_api_settings
from api.database.core import SessionLocal
from api.database.models import User, Session as DBSession, NodeState
from api.topic_validation import validate_learning_topic_with_moderation
from api.schemas.learning import (
    StartResponse,
    SessionStatusResponse,
    SessionSummary,
    SessionListResponse,
)
from api.services.graph_helpers import resolve_journey_orchestrator_v2

_settings = get_api_settings()


# ── Ownership guard ───────────────────────────────────────────


async def get_user_session(
    session_id: str, user_id: int, db: AsyncSession
) -> DBSession:
    """Fetch a session owned by the given user, or raise 404."""
    result = await db.execute(
        select(DBSession).filter(
            DBSession.id == session_id, DBSession.user_id == user_id
        )
    )
    db_session = result.scalars().first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


# ── Listing ───────────────────────────────────────────────────


async def list_user_sessions(
    user_id: int, db: AsyncSession, *, limit: int = 20, offset: int = 0
) -> SessionListResponse:
    """Paginated session listing, newest first, excluding archived."""
    count_result = await db.execute(
        select(func.count(DBSession.id))
        .filter(DBSession.user_id == user_id)
        .filter(DBSession.status != "archived")
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(DBSession)
        .filter(DBSession.user_id == user_id)
        .filter(DBSession.status != "archived")
        .order_by(desc(DBSession.created_at))
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()

    summaries = [
        SessionSummary(
            session_id=s.id,
            topic=s.topic or "",
            status=s.status or "unknown",
            created_at=s.created_at.isoformat() if s.created_at else "",
            overall_progress=0.0,
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=summaries, total=total)


# ── Creation ──────────────────────────────────────────────────


async def create_session(
    *,
    topic: str,
    course_mode: str,
    traversal_mode: str,
    user: User,
    db: AsyncSession,
    arq_pool: Any,
) -> StartResponse:
    """Validate the topic, persist a new session, and dispatch to ARQ."""
    # ── Per-user session cap ──────────────────────────────────
    active_count_result = await db.execute(
        select(func.count(DBSession.id))
        .filter(DBSession.user_id == user.id)
        .filter(DBSession.status.notin_(["archived", "completed", "error"]))
    )
    active_count = active_count_result.scalar() or 0
    if active_count >= _settings.max_active_sessions_per_user:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum of {_settings.max_active_sessions_per_user} active sessions reached. "
            "Archive or complete existing sessions first.",
        )

    topic_check = await validate_learning_topic_with_moderation(topic)
    if topic_check["status"] != "valid_learning_topic":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": topic_check["code"],
                "message": topic_check["message"],
                "suggestions": topic_check["suggestions"],
            },
        )

    safe_topic = topic_check["normalized_topic"]

    # Cross-session historical weak areas
    historical_weak_query = (
        select(NodeState.node_id)
        .join(DBSession)
        .filter(
            DBSession.user_id == user.id,
            NodeState.score != None,  # noqa: E711
            NodeState.score < 0.6,
        )
        .distinct()
    )
    hw_result = await db.execute(historical_weak_query)
    weak_topics = hw_result.scalars().all()

    session_id = str(uuid.uuid4())
    learner_profile = ", ".join(weak_topics) if weak_topics else ""
    journey_v2 = resolve_journey_orchestrator_v2(
        user.id, session_id, settings=_settings
    )

    db_session = DBSession(
        id=session_id,
        user_id=user.id,
        topic=safe_topic,
        langgraph_thread_id=session_id,
        status="initializing",
        current_phase="root",
        course_mode=course_mode,
    )
    db.add(db_session)
    await db.commit()

    # Dispatch to ARQ worker
    try:
        await arq_pool.enqueue_job(
            "start_learning_task",
            session_id,
            safe_topic,
            course_mode,
            traversal_mode,
            learner_profile,
            journey_v2,
        )
    except Exception as exc:
        db_session.status = "error"
        db_session.error_message = "Unable to enqueue learning job. Please try again."
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Queue unavailable while starting session: {exc}",
        )

    return StartResponse(
        session_id=session_id,
        message="Learning session started asynchronously. Connect to websocket for streaming.",
    )


# ── Status polling ────────────────────────────────────────────


async def get_session_status(
    db_session: DBSession,
) -> SessionStatusResponse:
    """Build a status response from the DB session record."""
    return SessionStatusResponse(
        session_id=db_session.id,
        status=db_session.status or "unknown",
        current_phase=db_session.current_phase,
        topic=db_session.topic or "",
        error_message=db_session.error_message,
    )


# ── Archival ──────────────────────────────────────────────────


async def archive_session(db_session: DBSession, db: AsyncSession) -> dict:
    """Soft-delete a session by marking it as archived."""
    db_session.status = "archived"
    await db.commit()
    return {"status": "archived", "session_id": db_session.id}


# ── WebSocket access ─────────────────────────────────────────


async def websocket_has_session_access(session_id: str, email: str) -> bool:
    """Check whether the user identified by *email* owns *session_id*."""
    if not session_id or not email:
        return False
    async with SessionLocal() as db:
        result = await db.execute(
            select(DBSession.id)
            .join(User, DBSession.user_id == User.id)
            .filter(DBSession.id == session_id, User.email == email)
        )
        return result.scalar_one_or_none() is not None
