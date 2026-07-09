"""
Quiz & evaluation endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.routers.auth import get_current_user
from api.schemas.learning import (
    EvaluateRequest,
    EvaluateResponse,
    EvaluationResult,
    QuizResponse,
)
from api.services.evaluation_service import (
    get_quiz as _get_quiz,
    submit_evaluation as _submit_evaluation,
    get_evaluation_result as _get_evaluation_result,
)
from api.services.session_service import get_user_session

router = APIRouter()


@router.get("/{session_id}/quiz", response_model=QuizResponse)
async def get_quiz(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Fetch the generated quiz for the current subtopic."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _get_quiz(session_id=session_id, db_session=db_session)


@router.post("/{session_id}/evaluate", response_model=EvaluateResponse, deprecated=True)
async def submit_evaluation(
    session_id: str,
    body: EvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Submit quiz answers for grading. Prefer /continue instead."""
    arq_pool = await _get_arq_pool()
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _submit_evaluation(
        session_id=session_id,
        db_session=db_session,
        answers=body.answers,
        arq_pool=arq_pool,
    )


@router.get("/{session_id}/evaluation", response_model=EvaluationResult)
async def get_evaluation(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get the latest evaluation result."""
    await get_user_session(session_id, current_user.id, db)
    return await _get_evaluation_result(session_id)


@router.get("/{session_id}/evaluation/result", response_model=EvaluationResult)
async def get_evaluation_result(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get the evaluation result — alias endpoint."""
    await get_user_session(session_id, current_user.id, db)
    return await _get_evaluation_result(session_id)


# ── ARQ pool helper ──────────────────────────────────────────

async def _get_arq_pool():
    from arq import create_pool
    from arq.connections import RedisSettings
    from api.config import get_api_settings

    settings = get_api_settings()
    return await create_pool(RedisSettings.from_dsn(settings.redis_url))
