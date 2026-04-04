import hashlib
import json
import time
import uuid
from typing import Any, Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from jose import JWTError, jwt

from api.config import get_api_settings
from api.database.core import get_db, SessionLocal
from api.database.models import User, Session as DBSession, NodeState
from api.routers.auth import get_current_user
from api.topic_validation import validate_learning_topic_with_moderation
from agent.nodes._mcq import validate_mcq_submission
from api.schemas.learning import (
    LearningRequest, StartResponse, LessonResponse,
    EvaluateRequest, EvaluateResponse, ProgressResponse,
    NextRequest, JourneyChoicesResponse,
    ContinueRequest, ContinueResponse, JourneyNextActionResponse,
    TutorContent, CuratorContent, CuratorResource,
    EvaluationResult, SubtopicProgress, NodeHierarchyMeta, WorkflowSnapshotResponse,
    SessionStatusResponse, SessionSummary, SessionListResponse,
    QuizResponse, QuizQuestion,
)
from api.engine.runner import get_current_state, set_next_choice
from api.engine.websocket import manager

router = APIRouter()

_settings = get_api_settings()
_LOCAL_LOCKS: dict[str, float] = {}
_LOCAL_IDEMPOTENCY: dict[str, tuple[float, dict[str, Any]]] = {}
_PROGRESS_HISTORY_LIMIT = 200


# ── WebSocket (with token auth) ──────────────────────────────

@router.websocket("/{session_id}/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(default=None),
):
    """
    WebSocket endpoint for real-time graph updates.
    Requires ?token=<jwt> query parameter for authentication.
    """
    # Authenticate via query param token
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    try:
        payload = jwt.decode(token, _settings.secret_key, algorithms=[_settings.jwt_algorithm])
        email: str = payload.get("sub")
        if email is None:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    allowed = await _websocket_has_session_access(session_id, email)
    if not allowed:
        await websocket.close(code=4003, reason="Session access denied")
        return

    await manager.connect(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket, session_id)


# ── Session Management ────────────────────────────────────────

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all learning sessions for the authenticated user, newest first."""
    # Efficient Count total
    count_result = await db.execute(
        select(func.count(DBSession.id))
        .filter(DBSession.user_id == current_user.id)
        .filter(DBSession.status != "archived")
    )
    total = count_result.scalar() or 0

    # Fetch page
    result = await db.execute(
        select(DBSession)
        .filter(DBSession.user_id == current_user.id)
        .filter(DBSession.status != "archived")
        .order_by(desc(DBSession.created_at))
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()

    summaries = []
    for s in sessions:
        summaries.append(SessionSummary(
            session_id=s.id,
            topic=s.topic or "",
            status=s.status or "unknown",
            created_at=s.created_at.isoformat() if s.created_at else "",
            overall_progress=0.0,  # Enriched below if available
        ))

    return SessionListResponse(sessions=summaries, total=total)


@router.post("/start", response_model=StartResponse)
async def start_learning(
    request: Request,
    payload: LearningRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Start a new learning session. Graph runs asynchronously via ARQ."""
    topic_check = await validate_learning_topic_with_moderation(payload.topic)
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

    # Fetch cross-session historical learner profile (weak areas)
    historical_weak_query = select(NodeState.node_id).join(DBSession).filter(
        DBSession.user_id == current_user.id,
        NodeState.score != None,
        NodeState.score < 0.6
    ).distinct()
    hw_result = await db.execute(historical_weak_query)
    weak_topics = hw_result.scalars().all()
    session_id = str(uuid.uuid4())
    learner_profile = ", ".join(weak_topics) if weak_topics else ""
    journey_orchestrator_v2 = _resolve_journey_orchestrator_v2(current_user.id, session_id)

    db_session = DBSession(
        id=session_id,
        user_id=current_user.id,
        topic=safe_topic,
        langgraph_thread_id=session_id,
        status="initializing",
        current_phase="root",
        course_mode=payload.course_mode,
    )
    db.add(db_session)
    await db.commit()

    # Dispatch to ARQ worker
    try:
        pool = request.app.state.arq_pool
        await pool.enqueue_job(
            "start_learning_task",
            session_id,
            safe_topic,
            payload.course_mode,
            payload.traversal_mode,
            learner_profile,
            journey_orchestrator_v2,
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


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Check the current execution status of a session (for HTTP polling)."""
    db_session = await _get_user_session(session_id, current_user.id, db)
    return SessionStatusResponse(
        session_id=db_session.id,
        status=db_session.status or "unknown",
        current_phase=db_session.current_phase,
        topic=db_session.topic or "",
        error_message=db_session.error_message,
    )


# ── Lesson & Evaluation ──────────────────────────────────────

@router.get("/{session_id}/lesson", response_model=LessonResponse)
async def get_lesson(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    node_id: str | None = Query(
        default=None,
        description="Optional node id to fetch lesson content for a specific node.",
    ),
):
    """Get lesson content for the active node or a specific node from session history."""
    db_session = await _get_user_session(session_id, current_user.id, db)

    # State guards
    if db_session.status in ["initializing", "running", "evaluating"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fetch lesson while session is '{db_session.status}'. Wait for 'ready'."
        )
    if db_session.status in ["error", "archived"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is '{db_session.status}' and cannot proceed."
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized or still processing initial steps.")

    state_vals = snapshot.values
    current_node = str(state_vals.get("current_node", "") or "")
    target_node = str(node_id or "").strip() or current_node
    subtopics = state_vals.get("subtopics", [])
    if target_node != current_node:
        catalog = state_vals.get("node_catalog", {})
        if not isinstance(catalog, dict) or target_node not in catalog:
            raise HTTPException(status_code=404, detail=f"Node '{target_node}' is not part of this session.")

    lesson = _resolve_lesson_payload(
        values=state_vals,
        target_node=target_node,
        current_node=current_node,
    )
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "LESSON_NOT_GENERATED",
                "message": f"Lesson content for node '{target_node}' is not generated yet.",
                "hint": "Select this node as your next branch and continue learning to generate it.",
            },
        )

    node_meta = _get_node_meta(state_vals, target_node)
    tutor_content, curator_content = _parse_lesson_payload(lesson)

    # Determine if this is a remediation lesson
    is_remediation = target_node not in subtopics if target_node else False

    return LessonResponse(
        session_id=session_id,
        node_id=target_node,
        tutor_content=tutor_content,
        curator_content=curator_content,
        is_remediation=is_remediation,
        parent_node_id=node_meta.get("parent_node_id"),
        depth=node_meta.get("depth"),
        node_kind=node_meta.get("node_kind"),
        path_from_root=node_meta.get("path_from_root", []),
        is_math_heavy=node_meta.get("is_math_heavy"),
        is_expanded=node_meta.get("is_expanded"),
    )


def _resolve_lesson_payload(values: dict[str, Any], target_node: str, current_node: str) -> dict[str, Any] | None:
    if target_node == current_node:
        current_lesson = values.get("lesson", {})
        if isinstance(current_lesson, dict) and current_lesson:
            return current_lesson

    history = values.get("history", [])
    if not isinstance(history, list):
        return None

    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "lesson":
            continue
        subtopic = str(entry.get("subtopic", "") or "").strip()
        if subtopic != target_node:
            continue
        lesson = entry.get("lesson", {})
        if isinstance(lesson, dict) and lesson:
            return lesson
    return None


def _parse_lesson_payload(lesson: dict[str, Any]) -> tuple[TutorContent | None, CuratorContent | None]:
    raw_tutor = lesson.get("tutor_content")
    tutor_content = None
    if isinstance(raw_tutor, dict):
        expl = raw_tutor.get("explanation", "")
        if isinstance(expl, dict):
            expl = json.dumps(expl, indent=2)
        elif not isinstance(expl, str):
            expl = str(expl)
        tutor_content = TutorContent(
            learning_objective=str(raw_tutor.get("learning_objective", "")),
            explanation=expl,
            examples=raw_tutor.get("examples", []),
            common_misconception=str(raw_tutor.get("common_misconception", "")),
            practice_task=str(raw_tutor.get("practice_task", "")),
            code_snippet=raw_tutor.get("code_snippet"),
        )

    raw_curator = lesson.get("curator_content")
    curator_content = None
    if isinstance(raw_curator, dict):
        curator_content = CuratorContent(
            articles=[
                CuratorResource(
                    title=a.get("title", ""),
                    url=a.get("url", ""),
                    description=a.get("description"),
                )
                for a in raw_curator.get("articles", []) if isinstance(a, dict)
            ],
            videos=[
                CuratorResource(
                    title=v.get("title", ""),
                    url=v.get("url", ""),
                    description=v.get("description"),
                )
                for v in raw_curator.get("videos", []) if isinstance(v, dict)
            ],
            courses=[
                CuratorResource(
                    title=c.get("title", ""),
                    url=c.get("url", ""),
                    description=c.get("description"),
                )
                for c in raw_curator.get("courses", []) if isinstance(c, dict)
            ],
            references=[str(r) for r in raw_curator.get("references", []) if isinstance(r, str)],
        )

    return tutor_content, curator_content


@router.get("/{session_id}/quiz", response_model=QuizResponse)
async def get_quiz(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Fetch the generated quiz questions for the current subtopic."""
    db_session = await _get_user_session(session_id, current_user.id, db)

    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is '{db_session.status}'. Wait for 'ready'."
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    vals = snapshot.values
    current_node = vals.get("current_node", "")
    quiz = vals.get("quiz", {})
    raw_questions = quiz.get("questions", [])
    if not isinstance(raw_questions, list):
        raw_questions = []

    questions: list[QuizQuestion] = []
    for idx, q in enumerate(raw_questions):
        if not isinstance(q, dict):
            continue
        raw_options = q.get("options", [])
        options = [str(o) for o in raw_options] if isinstance(raw_options, list) else []
        if len(options) == 0:
            continue
        questions.append(
            QuizQuestion(
                question_id=str(q.get("question_id", f"q{idx + 1}")),
                question=str(q.get("question", "")),
                options=options,
            )
        )

    return QuizResponse(
        session_id=session_id,
        node_id=current_node,
        questions=questions,
        question_count=int(quiz.get("question_count", len(questions))),
        numerical_target_ratio=float(quiz.get("numerical_target_ratio", 0.0)),
        actual_numerical_ratio=float(quiz.get("actual_numerical_ratio", 0.0)),
    )


@router.post("/{session_id}/evaluate", response_model=EvaluateResponse, deprecated=True)
async def submit_evaluation(
    response: Response,
    request: Request,
    session_id: str,
    eval_req: EvaluateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Deprecated endpoint retained for backward compatibility.
    Prefer POST /learning/{session_id}/continue with `answers`.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</learning/{session_id}/continue>; rel="successor-version"'
    db_session = await _get_user_session(session_id, current_user.id, db)

    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot evaluate while session is '{db_session.status}'."
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    waiting_on = _snapshot_next_nodes(snapshot)
    if "evaluator" not in waiting_on:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluation submission is only allowed when a quiz is awaiting grading.",
        )

    quiz_questions = snapshot.values.get("quiz", {}).get("questions", [])
    try:
        validated_answers = validate_mcq_submission(quiz_questions, eval_req.answers)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    # Dispatch to ARQ Worker
    pool = request.app.state.arq_pool
    await pool.enqueue_job("resume_learning_task", session_id, validated_answers)

    return EvaluateResponse(
        status="processing",
        message="Evaluation submitted and processing in background.",
    )


@router.get("/{session_id}/evaluation", response_model=EvaluationResult)
async def get_evaluation(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the latest evaluation result for the current subtopic."""
    await _get_user_session(session_id, current_user.id, db)

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    return _build_evaluation_result(snapshot.values)


@router.get("/{session_id}/evaluation/result", response_model=EvaluationResult)
async def get_evaluation_result(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the latest evaluation result for the current subtopic.
    Explicit alias endpoint for clients that prefer a '/result' suffix.
    """
    await _get_user_session(session_id, current_user.id, db)

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    return _build_evaluation_result(snapshot.values)


@router.get("/{session_id}/next-action", response_model=JourneyNextActionResponse)
async def get_next_action(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Return a UX-friendly state machine hint so frontend can render the next CTA.
    """
    db_session = await _get_user_session(session_id, current_user.id, db)
    snapshot = await get_current_state(session_id)

    if not snapshot or not snapshot.values:
        session_status = db_session.status or "unknown"
        if session_status in {"initializing", "running", "evaluating"}:
            return JourneyNextActionResponse(
                session_id=session_id,
                action="wait",
                status="waiting",
                message=f"Session is '{session_status}'. Wait for readiness.",
                required_input=None,
            )
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    payload = _build_next_action_payload(
        session_id=session_id,
        session_status=db_session.status or "unknown",
        values=snapshot.values,
        waiting_on=_snapshot_next_nodes(snapshot),
    )
    return JourneyNextActionResponse(**payload)


@router.post("/{session_id}/continue", response_model=ContinueResponse)
async def continue_learning(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    continue_req: ContinueRequest | None = None,
):
    """
    UX-first convenience endpoint.
    Executes the next logical step (evaluate or advance), or returns required input.
    """
    db_session = await _get_user_session(session_id, current_user.id, db)
    session_status = db_session.status or "unknown"
    req = continue_req or ContinueRequest()
    request_id = req.client_request_id or ""
    lock_key: str | None = None

    try:
        lock_ok, lock_key = await _acquire_progression_lock(session_id)
        if not lock_ok:
            return ContinueResponse(
                session_id=session_id,
                status="waiting",
                action="wait",
                message="A progression request is already in progress for this session.",
                enqueued=False,
                request_status="in_progress",
                request_id=request_id or None,
            )

        if session_status in {"initializing", "running", "evaluating"}:
            return ContinueResponse(
                session_id=session_id,
                status="waiting",
                action="wait",
                message=f"Session is '{session_status}'. Wait until it becomes 'ready'.",
                enqueued=False,
                request_status="accepted",
                request_id=request_id or None,
            )
        if session_status == "completed":
            return ContinueResponse(
                session_id=session_id,
                status="completed",
                action="completed",
                message="Learning journey is completed.",
                enqueued=False,
                request_status="accepted",
                request_id=request_id or None,
            )
        if session_status in {"error", "archived"}:
            return ContinueResponse(
                session_id=session_id,
                status="blocked",
                action="blocked",
                message=f"Session is '{session_status}' and cannot continue.",
                enqueued=False,
                request_status="accepted",
                request_id=request_id or None,
            )

        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        values = snapshot.values
        waiting_on = _snapshot_next_nodes(snapshot)
        journey_mode = _normalize_journey_mode(values.get("journey_mode"))
        previous_node = _derive_previous_node(values)
        can_go_back = bool(previous_node and "next" in waiting_on)
        v2_enabled = _is_journey_v2_enabled(values)

        fingerprint = _build_continue_fingerprint(values, waiting_on, req)
        resolved_request_id = request_id.strip() if request_id else f"auto:{hashlib.sha1(fingerprint.encode()).hexdigest()[:20]}"

        if v2_enabled:
            duplicate = await _idempotency_get(session_id, resolved_request_id)
            if duplicate:
                if duplicate.get("fingerprint") != fingerprint:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail="client_request_id was reused with a different request payload.",
                    )
                cached = duplicate.get("response")
                if isinstance(cached, dict):
                    cached["request_status"] = "duplicate"
                    cached["request_id"] = resolved_request_id
                    return ContinueResponse(**cached)
                return ContinueResponse(
                    session_id=session_id,
                    status="waiting",
                    action="wait",
                    message="A matching request is already in progress.",
                    enqueued=False,
                    request_status="in_progress",
                    request_id=resolved_request_id,
                )
            await _idempotency_set(
                session_id,
                resolved_request_id,
                {"fingerprint": fingerprint, "response": None},
            )

        if "evaluator" in waiting_on:
            options = _derive_forward_choices(values)
            traversal_mode = _normalize_traversal_mode(req.traversal_mode or values.get("traversal_mode"))
            recommendation = _recommend_next_node(values, options, traversal_mode)
            selected_node = str(req.selected_node or "").strip()

            if selected_node:
                if selected_node not in options:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail={
                            "code": "INVALID_SELECTED_NODE",
                            "message": "selected_node is not available from the current frontier.",
                            "allowed_options": options,
                        },
                    )
                await set_next_choice(
                    session_id,
                    selected_node=selected_node,
                    traversal_mode=req.traversal_mode,
                )
            elif req.traversal_mode:
                await set_next_choice(session_id, traversal_mode=req.traversal_mode)

            if req.answers is None:
                message = "Quiz answers are required to continue."
                if selected_node:
                    message = f"{message} Next node '{selected_node}' has been saved."
                response_obj = ContinueResponse(
                    session_id=session_id,
                    status="needs_input",
                    action="take_quiz",
                    message=message,
                    journey_mode=journey_mode,
                    can_go_back=can_go_back,
                    previous_node=previous_node,
                    options=options,
                    recommended_node=recommendation["node"],
                    recommendation_reason=recommendation["reason"],
                    recommendation_factors=recommendation["factors"],
                    required_input="answers",
                    enqueued=False,
                    request_status="accepted",
                    request_id=resolved_request_id,
                )
                if v2_enabled:
                    await _idempotency_set(
                        session_id,
                        resolved_request_id,
                        {"fingerprint": fingerprint, "response": response_obj.model_dump()},
                    )
                return response_obj

            quiz_questions = values.get("quiz", {}).get("questions", [])
            try:
                validated_answers = validate_mcq_submission(quiz_questions, req.answers)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

            pool = request.app.state.arq_pool
            try:
                await pool.enqueue_job("resume_learning_task", session_id, validated_answers)
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Queue unavailable while submitting evaluation: {exc}",
                )
            message = "Answers accepted. Evaluation is processing."
            if selected_node:
                message = f"{message} Next node '{selected_node}' is queued."
            response_obj = ContinueResponse(
                session_id=session_id,
                status="processing",
                action="submit_evaluation",
                message=message,
                journey_mode=journey_mode,
                can_go_back=can_go_back,
                previous_node=previous_node,
                options=options,
                recommended_node=recommendation["node"],
                recommendation_reason=recommendation["reason"],
                recommendation_factors=recommendation["factors"],
                enqueued=True,
                request_status="accepted",
                request_id=resolved_request_id,
            )
            if v2_enabled:
                await _idempotency_set(
                    session_id,
                    resolved_request_id,
                    {"fingerprint": fingerprint, "response": response_obj.model_dump()},
                )
            return response_obj

        evaluation = values.get("evaluation", {})
        completed_eval = isinstance(evaluation, dict) and evaluation.get("next_action") == "completed"
        can_advance = bool({"next", "bridge"} & set(waiting_on)) or completed_eval
        if can_advance:
            options = _derive_available_choices(values, waiting_on=waiting_on, enable_backtracking=v2_enabled)
            forward_options = _derive_forward_choices(values)
            traversal_mode = _normalize_traversal_mode(req.traversal_mode or values.get("traversal_mode"))
            recommendation = _recommend_next_node(values, forward_options, traversal_mode)
            selected_node = str(req.selected_node or "").strip()

            if selected_node and "next" not in waiting_on:
                response_obj = ContinueResponse(
                    session_id=session_id,
                    status="needs_input",
                    action="advance",
                    message="selected_node is not applicable for remediation-only advancement.",
                    journey_mode=journey_mode,
                    can_go_back=can_go_back,
                    previous_node=previous_node,
                    enqueued=False,
                    request_status="accepted",
                    request_id=resolved_request_id,
                )
                if v2_enabled:
                    await _idempotency_set(
                        session_id,
                        resolved_request_id,
                        {"fingerprint": fingerprint, "response": response_obj.model_dump()},
                    )
                return response_obj

            if "next" in waiting_on:
                if selected_node and selected_node not in options:
                    response_obj = ContinueResponse(
                        session_id=session_id,
                        status="needs_input",
                        action="choose_branch",
                        message="selected_node is not in available options.",
                        journey_mode=journey_mode,
                        can_go_back=can_go_back,
                        previous_node=previous_node,
                        options=options,
                        recommended_node=recommendation["node"],
                        recommendation_reason=recommendation["reason"],
                        recommendation_factors=recommendation["factors"],
                        required_input="selected_node",
                        enqueued=False,
                        request_status="accepted",
                        request_id=resolved_request_id,
                    )
                    if v2_enabled:
                        await _idempotency_set(
                            session_id,
                            resolved_request_id,
                            {"fingerprint": fingerprint, "response": response_obj.model_dump()},
                        )
                    return response_obj
                if not selected_node:
                    selected_node = recommendation["node"] or ""

            await set_next_choice(
                session_id,
                selected_node=selected_node if selected_node else None,
                traversal_mode=traversal_mode,
            )
            pool = request.app.state.arq_pool
            try:
                await pool.enqueue_job("advance_learning_task", session_id)
            except Exception as exc:
                try:
                    await set_next_choice(session_id, selected_node="")
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Queue unavailable while advancing session: {exc}",
                )
            response_obj = ContinueResponse(
                session_id=session_id,
                status="processing",
                action="advance",
                message="Advancing to the next step.",
                journey_mode=journey_mode,
                can_go_back=can_go_back,
                previous_node=previous_node,
                enqueued=True,
                options=options,
                recommended_node=recommendation["node"],
                recommendation_reason=recommendation["reason"],
                recommendation_factors=recommendation["factors"],
                request_status="accepted",
                request_id=resolved_request_id,
            )
            if v2_enabled:
                await _idempotency_set(
                    session_id,
                    resolved_request_id,
                    {"fingerprint": fingerprint, "response": response_obj.model_dump()},
                )
            return response_obj

        action_payload = _build_next_action_payload(
            session_id=session_id,
            session_status=session_status,
            values=values,
            waiting_on=waiting_on,
        )
        response_obj = ContinueResponse(
            session_id=session_id,
            status="blocked",
            action=action_payload["action"],
            message=action_payload["message"],
            journey_mode=action_payload["journey_mode"],
            can_go_back=action_payload["can_go_back"],
            previous_node=action_payload["previous_node"],
            enqueued=False,
            options=action_payload["options"],
            recommended_node=action_payload["recommended_node"],
            recommendation_reason=action_payload["recommendation_reason"],
            recommendation_factors=action_payload["recommendation_factors"],
            required_input=action_payload["required_input"],
            request_status="accepted",
            request_id=resolved_request_id,
        )
        if v2_enabled:
            await _idempotency_set(
                session_id,
                resolved_request_id,
                {"fingerprint": fingerprint, "response": response_obj.model_dump()},
            )
        return response_obj
    finally:
        if lock_key:
            await _release_progression_lock(lock_key)


@router.get("/{session_id}/choices", response_model=JourneyChoicesResponse)
async def get_journey_choices(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get the currently available branch choices for graph traversal."""
    db_session = await _get_user_session(session_id, current_user.id, db)
    if db_session.status in ["initializing", "running", "evaluating", "archived", "error"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fetch choices while session is '{db_session.status}'.",
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    vals = snapshot.values
    waiting_on = _snapshot_next_nodes(snapshot)
    traversal_mode = _normalize_traversal_mode(vals.get("traversal_mode"))
    journey_mode = _normalize_journey_mode(vals.get("journey_mode"))
    previous_node = _derive_previous_node(vals)
    v2_enabled = _is_journey_v2_enabled(vals)
    options = _derive_available_choices(vals, waiting_on=waiting_on, enable_backtracking=v2_enabled)
    forward_options = _derive_forward_choices(vals)
    recommendation = _recommend_next_node(vals, forward_options, traversal_mode)
    node_meta = _get_node_meta(vals, str(vals.get("current_node", "") or ""))

    return JourneyChoicesResponse(
        session_id=session_id,
        current_node=str(vals.get("current_node", "") or ""),
        traversal_mode=traversal_mode,
        journey_mode=journey_mode,
        can_go_back=bool(previous_node and "next" in waiting_on and v2_enabled),
        previous_node=previous_node if v2_enabled else None,
        options=options,
        waiting_on=waiting_on,
        recommended_node=recommendation["node"],
        recommendation_reason=recommendation["reason"],
        recommendation_factors=recommendation["factors"],
        parent_node_id=node_meta.get("parent_node_id"),
        depth=node_meta.get("depth"),
        node_kind=node_meta.get("node_kind"),
        path_from_root=node_meta.get("path_from_root", []),
        is_math_heavy=node_meta.get("is_math_heavy"),
        is_expanded=node_meta.get("is_expanded"),
        option_metadata=_build_option_metadata(vals, options),
    )


@router.post("/{session_id}/next", deprecated=True)
async def next_step(
    response: Response,
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    next_req: NextRequest | None = None,
):
    """
    Deprecated endpoint retained for backward compatibility.
    Prefer POST /learning/{session_id}/continue with optional `selected_node`.
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f'</learning/{session_id}/continue>; rel="successor-version"'
    db_session = await _get_user_session(session_id, current_user.id, db)
    lock_ok, lock_key = await _acquire_progression_lock(session_id)
    if not lock_ok:
        return {
            "status": "processing",
            "message": "A progression request is already in progress.",
            "request_status": "in_progress",
        }
    try:
        if db_session.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot advance while session is '{db_session.status}'."
            )

        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        waiting_on = _snapshot_next_nodes(snapshot)
        evaluation = snapshot.values.get("evaluation", {})
        completed_eval = isinstance(evaluation, dict) and evaluation.get("next_action") == "completed"
        if not ({"next", "bridge"} & set(waiting_on)) and not completed_eval:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Advance is only available after evaluation has completed.",
            )

        selected_node = ""
        traversal_mode = None
        if next_req:
            selected_node = str(next_req.selected_node or "").strip()
            traversal_mode = next_req.traversal_mode

        v2_enabled = _is_journey_v2_enabled(snapshot.values)
        if selected_node:
            if "next" not in waiting_on:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Branch selection is only available when advancing to the next graph node.",
                )
            options = _derive_available_choices(
                snapshot.values,
                waiting_on=waiting_on,
                enable_backtracking=v2_enabled,
            )
            if selected_node not in options:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"selected_node must be one of: {options}",
                )

        await set_next_choice(
            session_id,
            selected_node=selected_node if selected_node else None,
            traversal_mode=traversal_mode,
        )

        # Dispatch to ARQ worker
        pool = request.app.state.arq_pool
        try:
            await pool.enqueue_job("advance_learning_task", session_id)
        except Exception as exc:
            try:
                await set_next_choice(session_id, selected_node="")
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Queue unavailable while advancing session: {exc}",
            )
        return {
            "status": "processing",
            "message": "Graph advancing.",
            "request_status": "accepted",
        }
    finally:
        await _release_progression_lock(lock_key)


# ── Progress ──────────────────────────────────────────────────

@router.get("/{session_id}/progress", response_model=ProgressResponse)
async def get_progress(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get detailed progress for a learning session including per-subtopic status."""
    db_session = await _get_user_session(session_id, current_user.id, db)

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

    # Build typed subtopic progress list
    subtopic_progress = []
    for st in raw_subtopics:
        meta = graph_nodes.get(st, {})
        node_meta = node_catalog.get(st, {})
        if not isinstance(node_meta, dict):
            node_meta = {}
        path_from_root = node_meta.get("path_from_root", [])
        if not isinstance(path_from_root, list):
            path_from_root = []
        status = meta.get("status", "unlocked")
        if st == current_node:
            status = "active"
        subtopic_progress.append(SubtopicProgress(
            name=st,
            status=status,
            score=scores.get(st),
            attempts=meta.get("attempts", 0),
            parent_node_id=node_meta.get("parent_node_id"),
            depth=node_meta.get("depth"),
            node_kind=node_meta.get("node_kind"),
            path_from_root=path_from_root,
            is_math_heavy=node_meta.get("is_math_heavy"),
            is_expanded=node_meta.get("is_expanded"),
        ))

    total_count = len(raw_subtopics)
    completed_count = sum(1 for st in raw_subtopics if mastery.get(st, False))
    overall_progress = completed_count / total_count if total_count > 0 else 0.0
    history_payload = vals.get("history", [])
    if not isinstance(history_payload, list):
        history_payload = []
    history_payload = history_payload[-_PROGRESS_HISTORY_LIMIT:]

    return ProgressResponse(
        session_id=session_id,
        topic=vals.get("topic", "Unknown"),
        status=db_session.status or "active",
        subtopics=subtopic_progress,
        current_node=current_node,
        overall_progress=round(overall_progress, 2),
        completed_count=completed_count,
        total_count=total_count,
        history=history_payload,
        traversal_mode=_normalize_traversal_mode(vals.get("traversal_mode")),
        active_frontier=_normalize_node_list(vals.get("active_frontier", [])),
        current_path=_normalize_node_list(vals.get("current_path", [])),
        children_map=_normalize_children_map(vals.get("children_map", {})),
        node_catalog=_build_node_catalog_list(vals),
    )


@router.get("/{session_id}/workflow", response_model=WorkflowSnapshotResponse)
async def get_workflow_snapshot(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Return a single workflow-oriented payload that mirrors the agent state machine.
    Useful for clients that want one endpoint for orchestration state.
    """
    db_session = await _get_user_session(session_id, current_user.id, db)
    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        session_status = getattr(db_session, "status", None) or "unknown"
        waiting_on: list[str] = []
        action_payload = _build_next_action_payload(
            session_id=session_id,
            session_status=session_status,
            values={},
            waiting_on=waiting_on,
        )
        return WorkflowSnapshotResponse(
            session_id=session_id,
            status=session_status,
            current_phase=getattr(db_session, "current_phase", None),
            topic=str(getattr(db_session, "topic", "") or ""),
            current_node="",
            journey_mode=_normalize_journey_mode(None),
            traversal_mode=_normalize_traversal_mode(None),
            waiting_on=waiting_on,
            next_action=action_payload.get("action"),
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
    waiting_on = _snapshot_next_nodes(snapshot)
    action_payload = _build_next_action_payload(
        session_id=session_id,
        session_status=db_session.status or "unknown",
        values=vals,
        waiting_on=waiting_on,
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
        journey_mode=_normalize_journey_mode(vals.get("journey_mode")),
        traversal_mode=_normalize_traversal_mode(vals.get("traversal_mode")),
        waiting_on=waiting_on,
        next_action=action_payload.get("action"),
        options=action_payload.get("options", []),
        recommended_node=action_payload.get("recommended_node"),
        recommendation_reason=action_payload.get("recommendation_reason"),
        recommendation_factors=action_payload.get("recommendation_factors", {}),
        lesson_ready=bool(vals.get("lesson")),
        quiz_ready=bool(quiz.get("questions")),
        evaluation_ready="score" in evaluation,
        quiz_question_count=int(quiz.get("question_count", len(quiz.get("questions", [])) if isinstance(quiz.get("questions", []), list) else 0)),
        numerical_target_ratio=float(quiz.get("numerical_target_ratio", 0.0)),
        actual_numerical_ratio=float(quiz.get("actual_numerical_ratio", 0.0)),
        active_frontier=_normalize_node_list(vals.get("active_frontier", [])),
        current_path=_normalize_node_list(vals.get("current_path", [])),
        children_map=_normalize_children_map(vals.get("children_map", {})),
        node_catalog=_build_node_catalog_list(vals),
    )


# ── Delete / Archive ──────────────────────────────────────────

@router.delete("/{session_id}")
async def archive_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a session by setting its status to 'archived'."""
    db_session = await _get_user_session(session_id, current_user.id, db)
    db_session.status = "archived"
    await db.commit()
    return {"status": "archived", "session_id": session_id}


# ── Helpers ───────────────────────────────────────────────────

async def _get_user_session(session_id: str, user_id: int, db: AsyncSession) -> DBSession:
    """Fetch a session owned by the given user, or raise 404."""
    result = await db.execute(
        select(DBSession).filter(DBSession.id == session_id, DBSession.user_id == user_id)
    )
    db_session = result.scalars().first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


async def _websocket_has_session_access(session_id: str, email: str) -> bool:
    if not session_id or not email:
        return False
    async with SessionLocal() as db:
        result = await db.execute(
            select(DBSession.id)
            .join(User, DBSession.user_id == User.id)
            .filter(DBSession.id == session_id, User.email == email)
        )
        return result.scalar_one_or_none() is not None


def _snapshot_next_nodes(snapshot) -> list[str]:
    nodes = getattr(snapshot, "next", ()) or ()
    if isinstance(nodes, (list, tuple)):
        return [str(n) for n in nodes]
    return []


def _build_evaluation_result(values: dict[str, Any]) -> EvaluationResult:
    evaluation = values.get("evaluation", {})
    if not isinstance(evaluation, dict) or "score" not in evaluation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluation result is not available yet. Submit quiz answers first.",
        )

    return EvaluationResult(
        score=float(evaluation.get("score", 0.0)),
        weak_areas=evaluation.get("weak_areas", []),
        feedback=evaluation.get("feedback", ""),
        passed=bool(evaluation.get("passed", False)),
        next_action=str(evaluation.get("next_action", "next_topic")),
        question_results=evaluation.get("question_results", []),
        question_count=int(evaluation.get("question_count", evaluation.get("total_questions", 0))),
        numerical_target_ratio=float(evaluation.get("numerical_target_ratio", 0.0)),
        actual_numerical_ratio=float(evaluation.get("actual_numerical_ratio", 0.0)),
    )


def _normalize_journey_mode(value: str | None) -> str:
    mode = str(value or "learn").strip().lower()
    return mode if mode in {"learn", "review"} else "learn"


def _normalize_traversal_mode(value: str | None) -> str:
    mode = str(value or "dfs").strip().lower()
    return mode if mode in {"bfs", "dfs"} else "dfs"


def _recommend_next_node(values: dict, options: list[str], traversal_mode: str) -> dict[str, Any]:
    if not options:
        return {"node": None, "reason": None, "factors": {}}

    scores = values.get("scores", {})
    graph_nodes = values.get("graph_nodes", {})
    mastery = values.get("mastery", {})
    navigation_stack = values.get("navigation_stack", [])
    journey_mode = _normalize_journey_mode(values.get("journey_mode"))
    if not isinstance(scores, dict):
        scores = {}
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    if not isinstance(mastery, dict):
        mastery = {}
    if not isinstance(navigation_stack, list):
        navigation_stack = []
    node_catalog = values.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}

    recent = [str(n) for n in navigation_stack[-3:]]
    current_node = str(values.get("current_node", "") or "")
    current_meta = node_catalog.get(current_node, {})
    current_depth = _safe_int(current_meta.get("depth", 0), 0) if isinstance(current_meta, dict) else 0
    current_kind = str(current_meta.get("node_kind", "concept") or "concept").lower() if isinstance(current_meta, dict) else "concept"

    has_pending_concept = False
    for node in options:
        meta = node_catalog.get(node, {})
        kind = str(meta.get("node_kind", "concept") or "concept").lower() if isinstance(meta, dict) else "concept"
        if kind != "concept":
            continue
        if mastery.get(node, False):
            continue
        has_pending_concept = True
        break

    scored: list[tuple[str, float, dict[str, Any]]] = []
    for idx, node in enumerate(options):
        hist_score = scores.get(node)
        has_history = hist_score is not None
        if has_history:
            try:
                normalized = float(hist_score)
            except (TypeError, ValueError):
                normalized = 0.5
            historical_priority = (1.0 - max(0.0, min(1.0, normalized))) * 100.0
            unseen_bonus = 0.0
        else:
            normalized = None
            historical_priority = 35.0
            unseen_bonus = 15.0

        recency_penalty = -20.0 if node in recent else 0.0
        tiebreak = (-idx / 1000.0) if traversal_mode == "bfs" else (idx / 1000.0)
        attempts = 0
        node_meta = graph_nodes.get(node)
        if isinstance(node_meta, dict):
            attempts = int(node_meta.get("attempts", 0))
        attempt_penalty = -min(float(attempts), 5.0)
        node_meta = node_catalog.get(node, {})
        node_depth = _safe_int(node_meta.get("depth", 0), 0) if isinstance(node_meta, dict) else 0
        node_kind = str(node_meta.get("node_kind", "concept") or "concept").lower() if isinstance(node_meta, dict) else "concept"
        depth_delta = node_depth - current_depth
        depth_factor = float(depth_delta) if traversal_mode == "dfs" else float(-depth_delta)
        sequencing_bonus = 0.0
        if journey_mode == "learn":
            if node_kind == "concept":
                sequencing_bonus += 10.0
            elif node_kind == "advanced":
                sequencing_bonus -= 10.0
            if current_kind == "intro" and node_kind == "advanced":
                sequencing_bonus -= 8.0
            if has_pending_concept and node_kind == "advanced":
                sequencing_bonus -= 12.0

        total = (
            historical_priority
            + unseen_bonus
            + recency_penalty
            + tiebreak
            + attempt_penalty
            + depth_factor
            + sequencing_bonus
        )
        scored.append(
            (
                node,
                total,
                {
                    "historical_priority": round(historical_priority, 3),
                    "unseen_bonus": round(unseen_bonus, 3),
                    "recency_penalty": round(recency_penalty, 3),
                    "attempt_penalty": round(attempt_penalty, 3),
                    "depth_factor": round(depth_factor, 3),
                    "sequencing_bonus": round(sequencing_bonus, 3),
                    "node_kind": node_kind,
                    "journey_mode": journey_mode,
                    "traversal_tiebreak": round(tiebreak, 6),
                    "historical_score": normalized,
                },
            )
        )

    best_node, _, factors = max(scored, key=lambda x: x[1])
    reason = (
        f"Recommended by deterministic priority ({traversal_mode.upper()} mode): "
        "weaker/unseen areas first, foundational concept sequencing, recently visited nodes deprioritized, then traversal tie-break."
    )
    return {"node": best_node, "reason": reason, "factors": factors}


def _build_next_action_payload(
    *,
    session_id: str,
    session_status: str,
    values: dict,
    waiting_on: list[str],
) -> dict:
    current_node = str(values.get("current_node", "") or "")
    journey_mode = _normalize_journey_mode(values.get("journey_mode"))
    traversal_mode = _normalize_traversal_mode(values.get("traversal_mode"))
    v2_enabled = _is_journey_v2_enabled(values)
    previous_node = _derive_previous_node(values)
    can_go_back = bool(previous_node and "next" in waiting_on and v2_enabled)
    options = _derive_available_choices(values, waiting_on=waiting_on, enable_backtracking=v2_enabled)
    forward_options = _derive_forward_choices(values)
    recommendation = _recommend_next_node(values, forward_options, traversal_mode)
    node_meta = _get_node_meta(values, current_node)
    hierarchy_payload = {
        "parent_node_id": node_meta.get("parent_node_id"),
        "depth": node_meta.get("depth"),
        "node_kind": node_meta.get("node_kind"),
        "path_from_root": node_meta.get("path_from_root", []),
        "is_math_heavy": node_meta.get("is_math_heavy"),
        "is_expanded": node_meta.get("is_expanded"),
        "option_metadata": _build_option_metadata(values, options),
    }

    if session_status in {"initializing", "running", "evaluating"}:
        return {
            "session_id": session_id,
            "action": "wait",
            "status": "waiting",
            "message": f"Session is '{session_status}'. Wait for readiness.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }
    if session_status == "completed":
        return {
            "session_id": session_id,
            "action": "completed",
            "status": "completed",
            "message": "Learning journey completed.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }
    if session_status in {"archived", "error"}:
        return {
            "session_id": session_id,
            "action": "blocked",
            "status": "blocked",
            "message": f"Session is '{session_status}' and cannot continue.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }

    if "evaluator" in waiting_on:
        return {
            "session_id": session_id,
            "action": "take_quiz",
            "status": "ready",
            "message": "Submit quiz answers to continue. Optionally preselect your next branch.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": options,
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": recommendation["node"],
            "recommendation_reason": recommendation["reason"],
            "recommendation_factors": recommendation["factors"],
            "required_input": "answers",
            **hierarchy_payload,
        }

    evaluation = values.get("evaluation", {})
    completed_eval = isinstance(evaluation, dict) and evaluation.get("next_action") == "completed"
    if {"next", "bridge"} & set(waiting_on) or completed_eval:
        if "bridge" in waiting_on and "next" not in waiting_on:
            return {
                "session_id": session_id,
                "action": "advance_remediation",
                "status": "ready",
                "message": "Advance to remediation step.",
                "current_node": current_node,
                "waiting_on": waiting_on,
                "options": [],
                "traversal_mode": traversal_mode,
                "journey_mode": journey_mode,
                "can_go_back": can_go_back,
                "previous_node": previous_node if v2_enabled else None,
                "recommended_node": None,
                "recommendation_reason": None,
                "recommendation_factors": {},
                "required_input": None,
                **hierarchy_payload,
            }
        return {
            "session_id": session_id,
            "action": "choose_branch" if options else "advance",
            "status": "ready",
            "message": "Choose your next branch or continue with the recommended option.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": options,
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": recommendation["node"],
            "recommendation_reason": recommendation["reason"],
            "recommendation_factors": recommendation["factors"],
            "required_input": "selected_node" if options else None,
            **hierarchy_payload,
        }

    return {
        "session_id": session_id,
        "action": "wait",
        "status": "ready",
        "message": "No immediate action required. Refresh state shortly.",
        "current_node": current_node,
        "waiting_on": waiting_on,
        "options": options,
        "traversal_mode": traversal_mode,
        "journey_mode": journey_mode,
        "can_go_back": can_go_back,
        "previous_node": previous_node if v2_enabled else None,
        "recommended_node": recommendation["node"],
        "recommendation_reason": recommendation["reason"],
        "recommendation_factors": recommendation["factors"],
        "required_input": None,
        **hierarchy_payload,
    }


def _derive_available_choices(
    values: dict,
    waiting_on: list[str] | None = None,
    enable_backtracking: bool = False,
) -> list[str]:
    choices = list(_derive_forward_choices(values))
    waiting_on = waiting_on or []
    if "next" not in waiting_on or not enable_backtracking:
        return choices

    previous_node = _derive_previous_node(values)
    current_node = str(values.get("current_node", "") or "")
    if previous_node and previous_node != current_node and previous_node not in choices:
        choices.append(previous_node)
    return choices


def _derive_previous_node(values: dict) -> str | None:
    navigation_stack = values.get("navigation_stack", [])
    current_node = str(values.get("current_node", "") or "")
    if isinstance(navigation_stack, list):
        compact = [str(node).strip() for node in navigation_stack if str(node).strip()]
        if compact:
            if compact[-1] != current_node:
                compact.append(current_node)
            if len(compact) >= 2:
                candidate = compact[-2]
                if candidate and candidate != current_node:
                    return candidate

    history = values.get("history", [])
    if not isinstance(history, list):
        return None

    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "transition":
            node = str(entry.get("from_node", "")).strip()
            if node and node != current_node:
                return node
        if entry.get("type") == "evaluation":
            node = str(entry.get("subtopic", "")).strip()
            if node and node != current_node:
                return node
        if entry.get("type") == "review_evaluation":
            node = str(entry.get("subtopic", "")).strip()
            if node and node != current_node:
                return node
    return None


def _get_node_meta(values: dict, node_id: str | None) -> dict[str, Any]:
    if not node_id:
        return {}
    catalog = values.get("node_catalog", {})
    if not isinstance(catalog, dict):
        return {}
    raw = catalog.get(node_id, {})
    if not isinstance(raw, dict):
        return {}
    path = raw.get("path_from_root", [])
    if not isinstance(path, list):
        path = []
    return {
        "parent_node_id": raw.get("parent_node_id"),
        "depth": raw.get("depth"),
        "node_kind": raw.get("node_kind"),
        "path_from_root": path,
        "is_math_heavy": raw.get("is_math_heavy"),
        "is_expanded": raw.get("is_expanded"),
    }


def _build_node_catalog_list(values: dict) -> list[NodeHierarchyMeta]:
    catalog = values.get("node_catalog", {})
    if not isinstance(catalog, dict):
        return []
    graph_nodes = values.get("graph_nodes", {})
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    scores = values.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    out: list[NodeHierarchyMeta] = []
    for node_id, raw in catalog.items():
        if not isinstance(raw, dict):
            continue
        path_from_root = raw.get("path_from_root", [])
        if not isinstance(path_from_root, list):
            path_from_root = []
        graph_meta = graph_nodes.get(node_id, {}) if isinstance(graph_nodes.get(node_id, {}), dict) else {}
        out.append(
            NodeHierarchyMeta(
                node_id=str(node_id),
                parent_node_id=raw.get("parent_node_id"),
                depth=_safe_int(raw.get("depth", 0), 0),
                node_kind=raw.get("node_kind"),
                path_from_root=[str(n) for n in path_from_root],
                is_math_heavy=bool(raw.get("is_math_heavy", False)),
                is_expanded=bool(raw.get("is_expanded", False)),
                status=graph_meta.get("status"),
                score=_safe_float(scores.get(node_id), None),
                attempts=_safe_int(graph_meta.get("attempts", 0), 0) if graph_meta else 0,
            )
        )
    out.sort(key=lambda item: (item.depth if item.depth is not None else 0, item.node_id))
    return out


def _build_option_metadata(values: dict, options: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for node in options:
        out[node] = _get_node_meta(values, node)
    return out


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_node_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for node in value:
        normalized = str(node).strip()
        if normalized:
            out.append(normalized)
    return out


def _normalize_children_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for parent, children in value.items():
        parent_id = str(parent).strip()
        if not parent_id:
            continue
        child_list: list[str] = []
        if isinstance(children, list):
            for child in children:
                child_id = str(child).strip()
                if child_id:
                    child_list.append(child_id)
        out[parent_id] = child_list
    return out


def _derive_forward_choices(values: dict) -> list[str]:
    frontier = values.get("active_frontier", [])
    if isinstance(frontier, list):
        front_choices: list[str] = []
        mastery = values.get("mastery", {})
        if not isinstance(mastery, dict):
            mastery = {}
        current_node = str(values.get("current_node", "") or "")
        for node in frontier:
            normalized = str(node).strip()
            if not normalized or normalized == current_node or mastery.get(normalized, False):
                continue
            if normalized not in front_choices:
                front_choices.append(normalized)
        if front_choices:
            return front_choices

    raw_choices = values.get("available_choices", [])
    if isinstance(raw_choices, list):
        choices: list[str] = []
        for item in raw_choices:
            node = str(item).strip()
            if node and node not in choices:
                choices.append(node)
        if choices:
            return choices

    subtopics = values.get("subtopics", [])
    mastery = values.get("mastery", {})
    current_node = str(values.get("current_node", "") or "")
    if not isinstance(subtopics, list):
        return []
    if not isinstance(mastery, dict):
        mastery = {}

    derived: list[str] = []
    for st in subtopics:
        node = str(st).strip()
        if not node or node == current_node or mastery.get(node, False):
            continue
        if node not in derived:
            derived.append(node)
    return derived


def _resolve_journey_orchestrator_v2(user_id: int, seed_value: str) -> bool:
    settings = get_api_settings()
    if not settings.journey_orchestrator_v2_enabled:
        return False

    allowlist_raw = (settings.journey_orchestrator_v2_allowlist_user_ids or "").strip()
    if allowlist_raw:
        allowlist = {
            int(token.strip())
            for token in allowlist_raw.split(",")
            if token.strip().isdigit()
        }
        if user_id in allowlist:
            return True

    rollout = max(0, min(int(settings.journey_orchestrator_v2_rollout_percent), 100))
    if rollout <= 0:
        return False

    seed = f"{user_id}:{seed_value}"
    bucket = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
    return bucket < rollout


def _is_journey_v2_enabled(values: dict) -> bool:
    return bool(values.get("journey_orchestrator_v2", False))


def _build_continue_fingerprint(values: dict, waiting_on: list[str], req: ContinueRequest) -> str:
    normalized = {
        "current_node": str(values.get("current_node", "") or ""),
        "journey_mode": _normalize_journey_mode(values.get("journey_mode")),
        "waiting_on": sorted(waiting_on),
        "answers": req.answers if isinstance(req.answers, list) else None,
        "selected_node": str(req.selected_node or "").strip() or None,
        "traversal_mode": _normalize_traversal_mode(req.traversal_mode or values.get("traversal_mode")),
        "eval_action": values.get("evaluation", {}).get("next_action") if isinstance(values.get("evaluation"), dict) else None,
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _acquire_progression_lock(session_id: str) -> tuple[bool, str]:
    lock_key = f"journey:lock:{session_id}"
    ttl = max(1, int(get_api_settings().journey_orchestrator_lock_ttl_seconds))
    redis = Redis.from_url(get_api_settings().redis_url)
    try:
        acquired = await redis.set(lock_key, "1", ex=ttl, nx=True)
        if acquired:
            return True, lock_key
    except Exception:
        now = time.time()
        expires_at = _LOCAL_LOCKS.get(lock_key, 0.0)
        if expires_at <= now:
            _LOCAL_LOCKS[lock_key] = now + ttl
            return True, lock_key
        return False, lock_key
    finally:
        await redis.aclose()
    return False, lock_key


async def _release_progression_lock(lock_key: str) -> None:
    redis = Redis.from_url(get_api_settings().redis_url)
    try:
        await redis.delete(lock_key)
    except Exception:
        _LOCAL_LOCKS.pop(lock_key, None)
    finally:
        await redis.aclose()


async def _idempotency_get(session_id: str, request_id: str) -> dict[str, Any] | None:
    key = f"journey:idemp:{session_id}:{request_id}"
    redis = Redis.from_url(get_api_settings().redis_url)
    try:
        raw = await redis.get(key)
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        item = _LOCAL_IDEMPOTENCY.get(key)
        if not item:
            return None
        expires_at, payload = item
        if expires_at < time.time():
            _LOCAL_IDEMPOTENCY.pop(key, None)
            return None
        return payload
    finally:
        await redis.aclose()


async def _idempotency_set(session_id: str, request_id: str, payload: dict[str, Any]) -> None:
    key = f"journey:idemp:{session_id}:{request_id}"
    ttl = max(1, int(get_api_settings().journey_orchestrator_idempotency_ttl_seconds))
    redis = Redis.from_url(get_api_settings().redis_url)
    try:
        await redis.set(key, json.dumps(payload), ex=ttl)
    except Exception:
        _LOCAL_IDEMPOTENCY[key] = (time.time() + ttl, payload)
    finally:
        await redis.aclose()
