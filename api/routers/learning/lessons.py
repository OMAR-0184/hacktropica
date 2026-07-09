"""
Lesson retrieval endpoint.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.routers.auth import get_current_user
from api.schemas.learning import LessonResponse
from api.services.lesson_service import get_lesson as _get_lesson
from api.services.session_service import get_user_session

router = APIRouter()


@router.get("/{session_id}/lesson", response_model=LessonResponse)
async def get_lesson(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    node_id: Optional[str] = Query(default=None),
):
    """Retrieve lesson content for the current or a historical node."""
    db_session = await get_user_session(session_id, current_user.id, db)
    return await _get_lesson(
        session_id=session_id, db_session=db_session, node_id=node_id
    )
