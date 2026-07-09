"""
Session lifecycle endpoints — create, list, poll status, archive.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.routers.auth import get_current_user
from api.schemas.learning import (
    LearningRequest,
    StartResponse,
    SessionStatusResponse,
    SessionListResponse,
)
from api.services.session_service import (
    get_user_session,
    list_user_sessions,
    create_session,
    archive_session as _archive_session,
    get_session_status as _get_session_status,
)

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all learning sessions for the authenticated user."""
    return await list_user_sessions(current_user.id, db, limit=limit, offset=offset)


@router.post("/start", response_model=StartResponse)
async def start_learning(
    request: LearningRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Start a new asynchronous learning session."""
    arq_pool = await _get_arq_pool()
    return await create_session(
        topic=request.topic,
        course_mode=request.course_mode,
        traversal_mode=request.traversal_mode,
        user=current_user,
        db=db,
        arq_pool=arq_pool,
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Poll the current status of a session."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _get_session_status(db_session)


@router.delete("/{session_id}")
async def archive_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a session by marking it as archived."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _archive_session(db_session, db)


# ── ARQ pool helper ──────────────────────────────────────────

async def _get_arq_pool():
    """Lazily get the ARQ pool for enqueuing jobs."""
    from arq import create_pool
    from arq.connections import RedisSettings
    from api.config import get_api_settings

    settings = get_api_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
