"""
Quiz retrieval and evaluation submission.

Reads quiz/evaluation state from the LangGraph checkpoint and dispatches
grading jobs to the ARQ worker.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from agent.nodes._mcq import validate_mcq_submission
from api.engine.runner import get_current_state
from api.schemas.learning import (
    QuizResponse,
    QuizQuestion,
    EvaluateResponse,
    EvaluationResult,
)
from api.services.graph_helpers import snapshot_next_nodes


# ── Quiz retrieval ────────────────────────────────────────────


async def get_quiz(*, session_id: str, db_session) -> QuizResponse:
    """Fetch the generated quiz questions for the current subtopic."""
    if db_session.status in ["initializing", "error", "archived"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fetch quiz while session is '{db_session.status}'.",
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
        if not options:
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


# ── Evaluation submission (deprecated endpoint) ──────────────


async def submit_evaluation(
    *, session_id: str, db_session, answers: list[int], arq_pool: Any
) -> EvaluateResponse:
    """Validate answers and dispatch grading to the ARQ worker."""
    if db_session.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot evaluate while session is '{db_session.status}'.",
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")

    waiting_on = snapshot_next_nodes(snapshot)
    if "evaluator" not in waiting_on:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evaluation submission is only allowed when a quiz is awaiting grading.",
        )

    quiz_questions = snapshot.values.get("quiz", {}).get("questions", [])
    try:
        validated_answers = validate_mcq_submission(quiz_questions, answers)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )

    await arq_pool.enqueue_job("resume_learning_task", session_id, validated_answers)

    return EvaluateResponse(
        status="processing",
        message="Evaluation submitted and processing in background.",
    )


# ── Evaluation result retrieval ──────────────────────────────


async def get_evaluation_result(session_id: str) -> EvaluationResult:
    """Retrieve the latest evaluation result from graph state."""
    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=400, detail="Graph not initialized.")
    return build_evaluation_result(snapshot.values)


def build_evaluation_result(values: dict[str, Any]) -> EvaluationResult:
    """Transform raw evaluation dict into a typed response model."""
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
        question_count=int(
            evaluation.get("question_count", evaluation.get("total_questions", 0))
        ),
        numerical_target_ratio=float(evaluation.get("numerical_target_ratio", 0.0)),
        actual_numerical_ratio=float(evaluation.get("actual_numerical_ratio", 0.0)),
    )
