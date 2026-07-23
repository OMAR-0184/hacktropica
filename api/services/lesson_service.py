"""
Lesson retrieval, resolution, and construction.

Resolves lesson payloads from the current graph state or history,
parses raw dicts into typed Pydantic models, and generates starter
lesson fallbacks for nodes that haven't been taught yet.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status

from api.engine.runner import get_current_state, apply_state_updates
from api.schemas.learning import (
    LessonResponse,
    TutorContent,
    CuratorContent,
    CuratorResource,
)
from api.services.graph_helpers import get_node_meta

_GRAPH_HISTORY_LIMIT = 300


# ── Public API ────────────────────────────────────────────────


async def get_lesson(
    *, session_id: str, db_session, node_id: str | None
) -> LessonResponse:
    """
    Return lesson content for the active node or a specific historical node.

    Generates a starter lesson on-the-fly if no lesson exists yet.
    """
    # State guards
    if db_session.status in ["initializing"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fetch lesson while session is '{db_session.status}'. Wait for 'ready'.",
        )
    if db_session.status in ["error", "archived"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is '{db_session.status}' and cannot proceed.",
        )

    snapshot = await get_current_state(session_id)
    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=400,
            detail="Graph not initialized or still processing initial steps.",
        )

    state_vals = snapshot.values
    current_node = str(state_vals.get("current_node", "") or "")
    target_node = str(node_id or "").strip() or current_node
    subtopics = state_vals.get("subtopics", [])

    # Validate that the target node exists in the session
    if target_node != current_node:
        catalog = state_vals.get("node_catalog", {})
        if not isinstance(catalog, dict) or target_node not in catalog:
            raise HTTPException(
                status_code=404,
                detail=f"Node '{target_node}' is not part of this session.",
            )

    lesson = resolve_lesson_payload(
        values=state_vals,
        target_node=target_node,
        current_node=current_node,
    )

    # Generate starter lesson if none found
    if lesson is None:
        node_meta_raw = get_node_meta(state_vals, target_node)
        parent_node_id = str(
            node_meta_raw.get("parent_node_id") or current_node or ""
        ).strip()
        node_kind = str(node_meta_raw.get("node_kind", "concept") or "concept")
        lesson = build_starter_lesson_payload(
            topic=str(state_vals.get("topic", "") or ""),
            node_id=target_node,
            parent_node_id=parent_node_id or "Root",
            node_kind=node_kind,
            is_math_heavy=bool(node_meta_raw.get("is_math_heavy", False)),
        )
        try:
            updates = append_lesson_to_history(
                state_vals,
                target_node=target_node,
                lesson_payload=lesson,
                source="on_demand_starter",
            )
            await apply_state_updates(session_id, updates)
        except Exception:
            pass  # Lesson is still returned even if checkpoint persistence fails

    node_meta = get_node_meta(state_vals, target_node)
    tutor_content, curator_content = parse_lesson_payload(lesson)
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


# ── Lesson resolution ────────────────────────────────────────


def resolve_lesson_payload(
    values: dict[str, Any], target_node: str, current_node: str
) -> dict[str, Any] | None:
    """Find the lesson payload for *target_node* in live state or history."""
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


# ── Payload parsing ───────────────────────────────────────────


def parse_lesson_payload(
    lesson: dict[str, Any],
) -> tuple[TutorContent | None, CuratorContent | None]:
    """Convert raw lesson dict into typed Pydantic models."""
    tutor_content = _parse_tutor(lesson.get("tutor_content"))
    curator_content = _parse_curator(lesson.get("curator_content"))
    return tutor_content, curator_content


def _parse_tutor(raw: Any) -> TutorContent | None:
    if not isinstance(raw, dict):
        return None
    expl = raw.get("explanation", "")
    if isinstance(expl, dict):
        expl = json.dumps(expl, indent=2)
    elif not isinstance(expl, str):
        expl = str(expl)
    return TutorContent(
        learning_objective=str(raw.get("learning_objective", "")),
        explanation=expl,
        examples=raw.get("examples", []),
        common_misconception=str(raw.get("common_misconception", "")),
        practice_task=str(raw.get("practice_task", "")),
        code_snippet=raw.get("code_snippet"),
    )


def _parse_curator(raw: Any) -> CuratorContent | None:
    if not isinstance(raw, dict):
        return None
    return CuratorContent(
        articles=[
            CuratorResource(
                title=a.get("title", ""),
                url=a.get("url", ""),
                description=a.get("description"),
            )
            for a in raw.get("articles", [])
            if isinstance(a, dict)
        ],
        videos=[
            CuratorResource(
                title=v.get("title", ""),
                url=v.get("url", ""),
                description=v.get("description"),
            )
            for v in raw.get("videos", [])
            if isinstance(v, dict)
        ],
        courses=[
            CuratorResource(
                title=c.get("title", ""),
                url=c.get("url", ""),
                description=c.get("description"),
            )
            for c in raw.get("courses", [])
            if isinstance(c, dict)
        ],
        references=[str(r) for r in raw.get("references", []) if isinstance(r, str)],
    )


# ── Starter lesson fallback ──────────────────────────────────


def build_starter_lesson_payload(
    *,
    topic: str,
    node_id: str,
    parent_node_id: str,
    node_kind: str,
    is_math_heavy: bool,
) -> dict[str, Any]:
    """Generate a deterministic placeholder lesson for a new node."""
    level_hint = {
        "concept": "foundational concept",
        "advanced": "advanced topic",
        "remediation": "targeted remediation topic",
    }.get(str(node_kind).strip().lower(), "concept")

    math_hint = (
        "Include worked numeric examples and step-by-step calculations."
        if is_math_heavy
        else "Focus on intuition, patterns, and practical interpretation."
    )
    explanation = (
        f"This is a starter lesson for '{node_id}' under '{parent_node_id}' in '{topic}'. "
        f"Treat it as a {level_hint}. {math_hint}"
    ).strip()

    return {
        "tutor_content": {
            "learning_objective": f"Understand and apply {node_id} in the context of {topic}.",
            "explanation": explanation,
            "examples": [
                f"Identify where '{node_id}' appears in common {topic} problems.",
                f"Compare '{node_id}' with related concepts under '{parent_node_id}'.",
            ],
            "common_misconception": f"Assuming '{node_id}' is interchangeable with sibling concepts.",
            "practice_task": f"Solve 2 quick exercises using '{node_id}' and explain your reasoning.",
            "code_snippet": None,
        },
        "curator_content": {
            "articles": [],
            "videos": [],
            "courses": [],
            "references": [
                f"Review parent node: {parent_node_id}",
                f"Revisit broader topic: {topic}"
                if topic
                else f"Revisit related topic to {node_id}",
            ],
        },
    }


# ── History helpers ───────────────────────────────────────────


def append_lesson_entries(
    history: list[dict[str, Any]],
    *,
    target_node: str,
    lesson_payload: dict[str, Any],
    source: str,
) -> list[dict[str, Any]]:
    """Append a lesson entry and trim to the history limit."""
    out = list(history)
    out.append(
        {
            "type": "lesson",
            "subtopic": target_node,
            "lesson": lesson_payload,
            "source": source,
        }
    )
    return out[-_GRAPH_HISTORY_LIMIT:]


def append_lesson_to_history(
    values: dict[str, Any],
    *,
    target_node: str,
    lesson_payload: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    """Return a state-update dict that appends a lesson to the history."""
    history = values.get("history", [])
    if not isinstance(history, list):
        history = []
    return {
        "history": append_lesson_entries(
            list(history),
            target_node=target_node,
            lesson_payload=lesson_payload,
            source=source,
        )
    }
