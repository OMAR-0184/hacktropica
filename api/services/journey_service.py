"""
Journey orchestration — the continue/advance/next-action state machine.

This is the brain of the learner experience loop. It decides what the
frontend should render next (quiz, branch selector, wait, etc.) and
dispatches background work via ARQ when the learner advances.
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import HTTPException, status

from agent.nodes._mcq import validate_mcq_submission
from api.engine.runner import get_current_state, set_next_choice
from api.schemas.learning import (
    ContinueRequest,
    ContinueResponse,
    JourneyNextActionResponse,
    JourneyChoicesResponse,
)
from api.services.concurrency import (
    acquire_progression_lock,
    release_progression_lock,
    idempotency_get,
    idempotency_set,
)
from api.services.graph_helpers import (
    snapshot_next_nodes,
    normalize_journey_mode,
    normalize_traversal_mode,
    is_journey_v2_enabled,
    build_next_action_payload,
    derive_forward_choices,
    derive_available_choices,
    derive_previous_node,
    get_node_meta,
    build_option_metadata,
    build_continue_fingerprint,
)
from api.services.recommendation import recommend_next_node


# ── Next-action hint ──────────────────────────────────────────


async def get_next_action(*, session_id: str, db_session) -> JourneyNextActionResponse:
    """Return a UX-friendly state-machine hint for the frontend CTA."""
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

    payload = build_next_action_payload(
        session_id=session_id,
        session_status=db_session.status or "unknown",
        values=snapshot.values,
        waiting_on=snapshot_next_nodes(snapshot),
        recommend_fn=recommend_next_node,
    )
    return JourneyNextActionResponse(**payload)


# ── Journey choices ───────────────────────────────────────────


async def get_journey_choices(*, session_id: str, db_session) -> JourneyChoicesResponse:
    """Return the currently available branch choices for graph traversal."""
    if db_session.status in [
        "initializing",
        "running",
        "evaluating",
        "archived",
        "error",
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fetch choices while session is '{db_session.status}'.",
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    vals = snapshot.values
    waiting_on = snapshot_next_nodes(snapshot)
    traversal_mode = normalize_traversal_mode(vals.get("traversal_mode"))
    journey_mode = normalize_journey_mode(vals.get("journey_mode"))
    previous_node = derive_previous_node(vals)
    v2_enabled = is_journey_v2_enabled(vals)
    options = derive_available_choices(
        vals, waiting_on=waiting_on, enable_backtracking=v2_enabled
    )
    forward_options = derive_forward_choices(vals)
    recommendation = recommend_next_node(vals, forward_options, traversal_mode)
    node_meta = get_node_meta(vals, str(vals.get("current_node", "") or ""))

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
        option_metadata=build_option_metadata(vals, options),
    )


# ── Unified continue endpoint ────────────────────────────────


async def continue_journey(
    *,
    session_id: str,
    db_session,
    req: ContinueRequest,
    arq_pool: Any,
) -> ContinueResponse:
    """
    Execute the next logical step in the learning journey.

    Handles quiz submission, branch selection, and graph advancement
    with distributed locking and idempotency protection.
    """
    session_status = db_session.status or "unknown"
    request_id = req.client_request_id or ""
    lock_key: str | None = None

    try:
        lock_ok, lock_key = await acquire_progression_lock(session_id)
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

        # ── Status guards ─────────────────────────────────────
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
        waiting_on = snapshot_next_nodes(snapshot)
        journey_mode = normalize_journey_mode(values.get("journey_mode"))
        previous_node = derive_previous_node(values)
        can_go_back = bool(previous_node and "next" in waiting_on)
        v2_enabled = is_journey_v2_enabled(values)

        fingerprint = build_continue_fingerprint(values, waiting_on, req)
        resolved_request_id = (
            request_id.strip()
            if request_id
            else f"auto:{hashlib.sha1(fingerprint.encode()).hexdigest()[:20]}"
        )

        # ── Idempotency check (v2 only) ──────────────────────
        if v2_enabled:
            duplicate = await idempotency_get(session_id, resolved_request_id)
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
            await idempotency_set(
                session_id,
                resolved_request_id,
                {"fingerprint": fingerprint, "response": None},
            )

        # ── Branch: quiz awaiting answers ─────────────────────
        if "evaluator" in waiting_on:
            return await _handle_evaluator_waiting(
                session_id=session_id,
                values=values,
                waiting_on=waiting_on,
                req=req,
                arq_pool=arq_pool,
                journey_mode=journey_mode,
                can_go_back=can_go_back,
                previous_node=previous_node,
                v2_enabled=v2_enabled,
                fingerprint=fingerprint,
                resolved_request_id=resolved_request_id,
            )

        # ── Branch: advance to next node ──────────────────────
        evaluation = values.get("evaluation", {})
        completed_eval = (
            isinstance(evaluation, dict)
            and evaluation.get("next_action") == "completed"
        )
        can_advance = bool({"next", "bridge"} & set(waiting_on)) or completed_eval

        if can_advance:
            return await _handle_advance(
                session_id=session_id,
                values=values,
                waiting_on=waiting_on,
                req=req,
                arq_pool=arq_pool,
                journey_mode=journey_mode,
                can_go_back=can_go_back,
                previous_node=previous_node,
                v2_enabled=v2_enabled,
                fingerprint=fingerprint,
                resolved_request_id=resolved_request_id,
            )

        # ── Fallback: no actionable interrupt ─────────────────
        action_payload = build_next_action_payload(
            session_id=session_id,
            session_status=session_status,
            values=values,
            waiting_on=waiting_on,
            recommend_fn=recommend_next_node,
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
            await idempotency_set(
                session_id,
                resolved_request_id,
                {"fingerprint": fingerprint, "response": response_obj.model_dump()},
            )
        return response_obj
    finally:
        if lock_key:
            await release_progression_lock(lock_key)


# ── Deprecated /next endpoint ─────────────────────────────────


async def advance_next_step(
    *,
    session_id: str,
    db_session,
    selected_node: str | None,
    traversal_mode: str | None,
    arq_pool: Any,
) -> dict:
    """Legacy advance logic preserved for backward compatibility."""
    lock_ok, lock_key = await acquire_progression_lock(session_id)
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
                detail=f"Cannot advance while session is '{db_session.status}'.",
            )

        snapshot = await get_current_state(session_id)
        if not snapshot or not snapshot.values:
            raise HTTPException(status_code=400, detail="Graph not initialized.")

        waiting_on = snapshot_next_nodes(snapshot)
        evaluation = snapshot.values.get("evaluation", {})
        completed_eval = (
            isinstance(evaluation, dict)
            and evaluation.get("next_action") == "completed"
        )
        if not ({"next", "bridge"} & set(waiting_on)) and not completed_eval:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Advance is only available after evaluation has completed.",
            )

        sel = str(selected_node or "").strip()
        v2_enabled = is_journey_v2_enabled(snapshot.values)

        if sel:
            if "next" not in waiting_on:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Branch selection is only available when advancing to the next graph node.",
                )
            options = derive_available_choices(
                snapshot.values,
                waiting_on=waiting_on,
                enable_backtracking=v2_enabled,
            )
            if sel not in options:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"selected_node must be one of: {options}",
                )

        await set_next_choice(
            session_id,
            selected_node=sel if sel else None,
            traversal_mode=traversal_mode,
        )

        try:
            await arq_pool.enqueue_job("advance_learning_task", session_id)
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
        await release_progression_lock(lock_key)


# ── Internal handlers ─────────────────────────────────────────


async def _handle_evaluator_waiting(
    *,
    session_id,
    values,
    waiting_on,
    req,
    arq_pool,
    journey_mode,
    can_go_back,
    previous_node,
    v2_enabled,
    fingerprint,
    resolved_request_id,
) -> ContinueResponse:
    """Handle the case where the graph is paused waiting for quiz answers."""
    options = derive_forward_choices(values)
    traversal_mode = normalize_traversal_mode(
        req.traversal_mode or values.get("traversal_mode")
    )
    recommendation = recommend_next_node(values, options, traversal_mode)
    selected_node = str(req.selected_node or "").strip()

    # Pre-select next node if provided
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
            session_id, selected_node=selected_node, traversal_mode=req.traversal_mode
        )
    elif req.traversal_mode:
        await set_next_choice(session_id, traversal_mode=req.traversal_mode)

    # No answers provided — tell frontend to collect them
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
            await idempotency_set(
                session_id,
                resolved_request_id,
                {"fingerprint": fingerprint, "response": response_obj.model_dump()},
            )
        return response_obj

    # Answers provided — validate and dispatch
    quiz_questions = values.get("quiz", {}).get("questions", [])
    try:
        validated_answers = validate_mcq_submission(quiz_questions, req.answers)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )

    try:
        await arq_pool.enqueue_job(
            "resume_learning_task", session_id, validated_answers
        )
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
        await idempotency_set(
            session_id,
            resolved_request_id,
            {"fingerprint": fingerprint, "response": response_obj.model_dump()},
        )
    return response_obj


async def _handle_advance(
    *,
    session_id,
    values,
    waiting_on,
    req,
    arq_pool,
    journey_mode,
    can_go_back,
    previous_node,
    v2_enabled,
    fingerprint,
    resolved_request_id,
) -> ContinueResponse:
    """Handle the case where the learner can advance to the next node."""
    options = derive_available_choices(
        values, waiting_on=waiting_on, enable_backtracking=v2_enabled
    )
    forward_options = derive_forward_choices(values)
    traversal_mode = normalize_traversal_mode(
        req.traversal_mode or values.get("traversal_mode")
    )
    recommendation = recommend_next_node(values, forward_options, traversal_mode)
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
            await idempotency_set(
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
                await idempotency_set(
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

    try:
        await arq_pool.enqueue_job("advance_learning_task", session_id)
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
        await idempotency_set(
            session_id,
            resolved_request_id,
            {"fingerprint": fingerprint, "response": response_obj.model_dump()},
        )
    return response_obj
