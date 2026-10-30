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
    if db_session.status in ["initializing", "running"]:
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

    # For Markdown, check if it's nested in the lesson_payload (saved as "markdown").
    markdown_data = {}
    if isinstance(lesson, dict):
        markdown_data = lesson.get("markdown") or lesson.get("markdown_content") or {}
    
    # Also check live state for markdown_content (set by lesson_generator).
    # ONLY do this if the requested node is the current active node.
    if not markdown_data and target_node == current_node:
        markdown_data = state_vals.get("markdown_content", {})
        if not isinstance(markdown_data, dict):
            markdown_data = {}

    # Handle legacy nested dictionary bug in markdown_source
    md_source = markdown_data.get("markdown_source")
    if isinstance(md_source, dict):
        md_source = md_source.get("markdown_source")
        
    return LessonResponse(
        session_id=session_id,
        node_id=target_node,
        tutor_content=tutor_content,
        curator_content=curator_content,
        markdown_source=md_source or None,
        markdown_valid=bool(markdown_data.get("markdown_valid", False)),
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

    # Core explanation: prefer new field, fall back to legacy.
    core_expl = raw.get("core_explanation", "")
    if isinstance(core_expl, dict):
        core_expl = json.dumps(core_expl, indent=2)
    elif not isinstance(core_expl, str):
        core_expl = str(core_expl)

    # Legacy explanation field.
    expl = raw.get("explanation", "")
    if isinstance(expl, dict):
        expl = json.dumps(expl, indent=2)
    elif not isinstance(expl, str):
        expl = str(expl)

    # If core_explanation is empty, use legacy explanation.
    if not core_expl.strip() and expl.strip():
        core_expl = expl
    # If legacy explanation is empty, derive from core_explanation.
    if not expl.strip() and core_expl.strip():
        expl = core_expl

    # Worked examples: prefer new field, fall back to legacy 'examples'.
    worked_examples = raw.get("worked_examples", [])
    if not isinstance(worked_examples, list):
        worked_examples = []
    legacy_examples = raw.get("examples", [])
    if not isinstance(legacy_examples, list):
        legacy_examples = []
    if not worked_examples and legacy_examples:
        worked_examples = legacy_examples
    if not legacy_examples and worked_examples:
        legacy_examples = worked_examples

    # Summary field.
    summary = raw.get("summary", [])
    if not isinstance(summary, list):
        summary = [str(summary)] if summary else []

    return TutorContent(
        hook=str(raw.get("hook", "") or ""),
        prior_knowledge=str(raw.get("prior_knowledge", "") or ""),
        learning_objective=str(raw.get("learning_objective", "") or ""),
        core_explanation=core_expl,
        worked_examples=[str(e) for e in worked_examples],
        visual_diagram_description=str(raw.get("visual_diagram_description", "") or ""),
        common_misconception=str(raw.get("common_misconception", "") or ""),
        practice_task=str(raw.get("practice_task", "") or ""),
        transfer_prompt=str(raw.get("transfer_prompt", "") or ""),
        summary=[str(s) for s in summary],
        code_snippet=raw.get("code_snippet"),
        # Legacy fields.
        explanation=expl,
        examples=[str(e) for e in legacy_examples],
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
