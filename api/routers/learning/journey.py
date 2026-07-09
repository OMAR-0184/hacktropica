"""
Journey orchestration endpoints — continue, next-action, choices, advance.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.routers.auth import get_current_user
from api.schemas.learning import (
    NextRequest,
    ContinueRequest,
    ContinueResponse,
    JourneyChoicesResponse,
    JourneyNextActionResponse,
)
from api.services.journey_service import (
    get_next_action as _get_next_action,
    continue_journey as _continue_journey,
    get_journey_choices as _get_journey_choices,
    advance_next_step as _advance_next_step,
)
from api.services.session_service import get_user_session

router = APIRouter()


@router.get("/{session_id}/next-action", response_model=JourneyNextActionResponse)
async def get_next_action(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Return the recommended next CTA for the frontend."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _get_next_action(session_id=session_id, db_session=db_session)


@router.post("/{session_id}/continue", response_model=ContinueResponse)
async def continue_learning(
    session_id: str,
    body: ContinueRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Unified endpoint — submit answers and/or advance the journey."""
    arq_pool = await _get_arq_pool()
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _continue_journey(
        session_id=session_id,
        db_session=db_session,
        req=body,
        arq_pool=arq_pool,
    )


@router.get("/{session_id}/choices", response_model=JourneyChoicesResponse)
async def get_journey_choices(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List the currently available branch choices."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _get_journey_choices(session_id=session_id, db_session=db_session)


@router.post("/{session_id}/next", deprecated=True)
async def next_step(
    session_id: str,
    body: NextRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Advance to the next topic. Prefer /continue instead."""
    arq_pool = await _get_arq_pool()
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _advance_next_step(
        session_id=session_id,
        db_session=db_session,
        selected_node=body.selected_node,
        traversal_mode=body.traversal_mode,
        arq_pool=arq_pool,
    )


# ── ARQ pool helper ──────────────────────────────────────────

async def _get_arq_pool():
    from arq import create_pool
    from arq.connections import RedisSettings
    from api.config import get_api_settings

    settings = get_api_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
