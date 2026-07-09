"""
Progress & workflow snapshot endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.core import get_db
from api.database.models import User
from api.engine.runner import get_current_state
from api.routers.auth import get_current_user
from api.schemas.learning import (
    ProgressResponse,
    SubtopicProgress,
    WorkflowSnapshotResponse,
)
from api.services.graph_helpers import (
    snapshot_next_nodes,
    normalize_journey_mode,
    normalize_traversal_mode,
    normalize_node_list,
    normalize_children_map,
    is_journey_v2_enabled,
    build_next_action_payload,
    build_node_catalog_list,
)
from api.services.recommendation import recommend_next_node
from api.services.session_service import get_user_session

router = APIRouter()
_PROGRESS_HISTORY_LIMIT = 200


@router.get("/{session_id}/progress", response_model=ProgressResponse)
async def get_progress(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Detailed per-subtopic progress for a session."""
    db_session = await get_user_session(session_id, current_user.id, db)
    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    vals = snapshot.values
    raw_subtopics = vals.get("subtopics", [])
    graph_nodes = vals.get("graph_nodes", {})
    node_catalog = vals.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}
    scores = vals.get("scores", {})
    mastery = vals.get("mastery", {})
    current_node = vals.get("current_node", "")

    subtopic_progress = []
    for st in raw_subtopics:
        meta = graph_nodes.get(st, {})
        nm = node_catalog.get(st, {})
        if not isinstance(nm, dict):
            nm = {}
        path = nm.get("path_from_root", [])
        if not isinstance(path, list):
            path = []
        st_status = meta.get("status", "unlocked")
        if st == current_node:
            st_status = "active"
        subtopic_progress.append(
            SubtopicProgress(
                name=st,
                status=st_status,
                score=scores.get(st),
                attempts=meta.get("attempts", 0),
                parent_node_id=nm.get("parent_node_id"),
                depth=nm.get("depth"),
                node_kind=nm.get("node_kind"),
                path_from_root=path,
                is_math_heavy=nm.get("is_math_heavy"),
                is_expanded=nm.get("is_expanded"),
            )
        )

    total_count = len(raw_subtopics)
    completed_count = sum(1 for st in raw_subtopics if mastery.get(st, False))
    history = vals.get("history", [])
    if not isinstance(history, list):
        history = []

    return ProgressResponse(
        session_id=session_id,
        topic=vals.get("topic", "Unknown"),
        status=db_session.status or "active",
        subtopics=subtopic_progress,
        current_node=current_node,
        overall_progress=round(completed_count / total_count, 2)
        if total_count
        else 0.0,
        completed_count=completed_count,
        total_count=total_count,
        history=history[-_PROGRESS_HISTORY_LIMIT:],
        traversal_mode=normalize_traversal_mode(vals.get("traversal_mode")),
        active_frontier=normalize_node_list(vals.get("active_frontier", [])),
        current_path=normalize_node_list(vals.get("current_path", [])),
        children_map=normalize_children_map(vals.get("children_map", {})),
        node_catalog=build_node_catalog_list(vals),
    )


@router.get("/{session_id}/workflow", response_model=WorkflowSnapshotResponse)
async def get_workflow_snapshot(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Single workflow-oriented payload mirroring the agent state machine."""
    db_session = await get_user_session(session_id, current_user.id, db)
    snapshot = await get_current_state(session_id)

    if not snapshot or not snapshot.values:
        session_status = getattr(db_session, "status", None) or "unknown"
        action_payload = build_next_action_payload(
            session_id=session_id,
            session_status=session_status,
            values={},
            waiting_on=[],
            recommend_fn=recommend_next_node,
        )
        return WorkflowSnapshotResponse(
            session_id=session_id,
            status=session_status,
            current_phase=getattr(db_session, "current_phase", None),
            topic=str(getattr(db_session, "topic", "") or ""),
            current_node="",
            journey_mode=normalize_journey_mode(None),
            traversal_mode=normalize_traversal_mode(None),
            waiting_on=[],
            next_action=action_payload.get("action"),
            orchestrator_reasoning=None,
            options=action_payload.get("options", []),
            recommended_node=action_payload.get("recommended_node"),
            recommendation_reason=action_payload.get("recommendation_reason"),
            recommendation_factors=action_payload.get("recommendation_factors", {}),
            lesson_ready=False,
            quiz_ready=False,
            evaluation_ready=False,
            quiz_question_count=0,
            numerical_target_ratio=0.0,
            actual_numerical_ratio=0.0,
            active_frontier=[],
            current_path=[],
            children_map={},
            node_catalog=[],
        )

    vals = snapshot.values
    waiting_on = snapshot_next_nodes(snapshot)
    action_payload = build_next_action_payload(
        session_id=session_id,
        session_status=db_session.status or "unknown",
        values=vals,
        waiting_on=waiting_on,
        recommend_fn=recommend_next_node,
    )
    quiz = vals.get("quiz", {})
    if not isinstance(quiz, dict):
        quiz = {}
    evaluation = vals.get("evaluation", {})
    if not isinstance(evaluation, dict):
        evaluation = {}

    return WorkflowSnapshotResponse(
        session_id=session_id,
        status=getattr(db_session, "status", None) or "unknown",
        current_phase=getattr(db_session, "current_phase", None),
        topic=str(vals.get("topic", getattr(db_session, "topic", "") or "") or ""),
        current_node=str(vals.get("current_node", "") or ""),
        journey_mode=normalize_journey_mode(vals.get("journey_mode")),
        traversal_mode=normalize_traversal_mode(vals.get("traversal_mode")),
        waiting_on=waiting_on,
        next_action=action_payload.get("action"),
        orchestrator_reasoning=str(vals.get("orchestrator_reasoning", "") or ""),
        options=action_payload.get("options", []),
        recommended_node=action_payload.get("recommended_node"),
        recommendation_reason=action_payload.get("recommendation_reason"),
        recommendation_factors=action_payload.get("recommendation_factors", {}),
        lesson_ready=bool(vals.get("lesson")),
        quiz_ready=bool(quiz.get("questions")),
        evaluation_ready="score" in evaluation,
        quiz_question_count=int(
            quiz.get(
                "question_count",
                len(quiz.get("questions", []))
                if isinstance(quiz.get("questions", []), list)
                else 0,
            )
        ),
        numerical_target_ratio=float(quiz.get("numerical_target_ratio", 0.0)),
        actual_numerical_ratio=float(quiz.get("actual_numerical_ratio", 0.0)),
        active_frontier=normalize_node_list(vals.get("active_frontier", [])),
        current_path=normalize_node_list(vals.get("current_path", [])),
        children_map=normalize_children_map(vals.get("children_map", {})),
        node_catalog=build_node_catalog_list(vals),
    )
