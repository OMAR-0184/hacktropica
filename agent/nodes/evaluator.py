"""
evaluator_node — Grades the user's submitted quiz answers against the standard answers.
"""

from __future__ import annotations

from typing import Any

from agent.config import get_settings
from agent.nodes._mcq import determine_next_action, grade_mcq
from agent.nodes._tree import build_node_meta, generate_child_blueprint, infer_math_heavy
from agent.state import CognimapState

_HISTORY_LIMIT = 300


async def evaluator_node(state: CognimapState) -> dict[str, Any]:
    """Score the user's quiz answers deterministically (no LLM grading)."""
    settings = get_settings()
    current = state["current_node"]
    quiz_questions = state.get("quiz", {}).get("questions", [])
    user_answers = state.get("evaluation", {}).get("user_answers", [])
    subtopics = list(state.get("subtopics", []))
    remediation_count = int(state.get("remediation_count", 0))
    history = list(state.get("history", []))
    mastery_state = dict(state.get("mastery", {}))
    graph_nodes = dict(state.get("graph_nodes", {}))
    node_catalog = dict(state.get("node_catalog", {}))
    parent_map = dict(state.get("parent_map", {}))
    children_map = dict(state.get("children_map", {}))
    expanded_nodes = list(state.get("expanded_nodes", []))
    active_frontier = list(state.get("active_frontier", []))
    journey_mode = str(state.get("journey_mode", "learn") or "learn").lower()
    if journey_mode not in {"learn", "review"}:
        journey_mode = "learn"

    evaluation = grade_mcq(
        subtopic=current,
        quiz_questions=quiz_questions,
        user_answers=user_answers,
        subtopics=subtopics,
        remediation_count=remediation_count,
        max_remediation=settings.max_remediation,
        mastery_threshold=settings.mastery_threshold,
        history=history,
        mastery=mastery_state,
    )
    quiz_meta = state.get("quiz", {})
    if not isinstance(quiz_meta, dict):
        quiz_meta = {}
    evaluation["question_count"] = int(quiz_meta.get("question_count", len(quiz_questions)))
    evaluation["numerical_target_ratio"] = float(quiz_meta.get("numerical_target_ratio", 0.0))
    evaluation["actual_numerical_ratio"] = float(quiz_meta.get("actual_numerical_ratio", 0.0))

    score = float(evaluation.get("score", 0.0))
    passed = bool(evaluation.get("passed", False))

    weak = evaluation.get("weak_areas", [])
    if not isinstance(weak, list):
        weak = []

    scores = dict(state.get("scores", {}))
    scores[current] = score

    weak_areas = dict(state.get("weak_areas", {}))
    weak_areas[current] = weak

    mastery = dict(state.get("mastery", {}))

    if passed:
        try:
            (
                subtopics,
                graph_nodes,
                node_catalog,
                parent_map,
                children_map,
                expanded_nodes,
                active_frontier,
            ) = await _expand_curriculum_on_pass(
                state=state,
                current=current,
                subtopics=subtopics,
                graph_nodes=graph_nodes,
                node_catalog=node_catalog,
                parent_map=parent_map,
                children_map=children_map,
                expanded_nodes=expanded_nodes,
                active_frontier=active_frontier,
                mastery=mastery,
                weak_areas=weak,
            )
        except Exception as exc:
            history.append(
                {
                    "type": "generation_error",
                    "subtopic": current,
                    "stage": "child_expansion",
                    "error": str(exc),
                }
            )

    next_action = determine_next_action(
        passed=passed,
        current_node=current,
        subtopics=subtopics,
        remediation_count=remediation_count,
        max_remediation=settings.max_remediation,
        history=history,
        mastery=mastery,
    )
    evaluation["next_action"] = next_action
    completed = next_action == "completed"
    parent_subtopic = _find_bridge_parent(history, current) if current not in subtopics else None

    if current in graph_nodes:
        node_meta = dict(graph_nodes[current])
        node_meta["attempts"] = int(node_meta.get("attempts", 0)) + 1
        node_meta["best_score"] = max(float(node_meta.get("best_score", 0.0)), score)
        if completed:
            node_meta["status"] = "mastered"
        graph_nodes[current] = node_meta

    if parent_subtopic and parent_subtopic in graph_nodes and completed:
        parent_meta = dict(graph_nodes[parent_subtopic])
        parent_meta["status"] = "mastered"
        graph_nodes[parent_subtopic] = parent_meta

    if completed:
        mastery[current] = True
        if parent_subtopic:
            mastery[parent_subtopic] = True

    available_choices = []
    for node in active_frontier:
        if node == current:
            continue
        if mastery.get(node, False):
            continue
        if node not in available_choices:
            available_choices.append(node)

    history = list(state.get("history", []))
    history.append({
        "type": "review_evaluation" if journey_mode == "review" else "evaluation",
        "subtopic": current,
        "score": score,
        "feedback": evaluation.get("feedback", ""),
        "weak_areas": weak,
        "passed": passed,
        "next_action": evaluation.get("next_action", "next_topic"),
        "journey_mode": journey_mode,
    })
    history = history[-_HISTORY_LIMIT:]

    return {
        "evaluation": evaluation,
        "scores": scores,
        "weak_areas": weak_areas,
        "mastery": mastery,
        "subtopics": subtopics,
        "graph_nodes": graph_nodes,
        "node_catalog": node_catalog,
        "parent_map": parent_map,
        "children_map": children_map,
        "expanded_nodes": expanded_nodes,
        "active_frontier": active_frontier,
        "available_choices": available_choices,
        "history": history,
    }


async def _expand_curriculum_on_pass(
    *,
    state: CognimapState,
    current: str,
    subtopics: list[str],
    graph_nodes: dict[str, Any],
    node_catalog: dict[str, Any],
    parent_map: dict[str, Any],
    children_map: dict[str, Any],
    expanded_nodes: list[str],
    active_frontier: list[str],
    mastery: dict[str, bool],
    weak_areas: list[str],
) -> tuple[list[str], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[str], list[str]]:
    settings = get_settings()
    topic = str(state.get("topic", "") or "")
    course_mode = str(state.get("course_mode", "detailed") or "detailed")
    current_meta = dict(node_catalog.get(current, {}))
    parent_path = current_meta.get("path_from_root", [])
    if not isinstance(parent_path, list):
        parent_path = [current]
    if not parent_path:
        parent_path = [current]

    current_depth = int(current_meta.get("depth", len(parent_path) - 1))
    node_kind = str(current_meta.get("node_kind", "concept") or "concept")
    if node_kind == "remediation":
        return (
            subtopics,
            graph_nodes,
            node_catalog,
            parent_map,
            children_map,
            expanded_nodes,
            active_frontier,
        )

    if current_depth >= int(settings.max_tree_depth):
        current_meta["is_expanded"] = True
        node_catalog[current] = current_meta
        if current not in expanded_nodes:
            expanded_nodes.append(current)
        return (
            subtopics,
            graph_nodes,
            node_catalog,
            parent_map,
            children_map,
            expanded_nodes,
            active_frontier,
        )

    if bool(current_meta.get("is_expanded", False)) or current in expanded_nodes:
        return (
            subtopics,
            graph_nodes,
            node_catalog,
            parent_map,
            children_map,
            expanded_nodes,
            active_frontier,
        )

    existing_titles = {str(k).strip().lower() for k in node_catalog.keys()}
    existing_titles.update(str(st).strip().lower() for st in subtopics)
    child_blueprint = await generate_child_blueprint(
        topic=topic,
        parent_node=current,
        parent_depth=current_depth,
        weak_areas=weak_areas,
        min_children=settings.tree_min_children,
        max_children=settings.tree_max_children,
        course_mode=course_mode,
        existing_titles=existing_titles,
    )

    current_children = list(children_map.get(current, []))
    child_depth = current_depth + 1
    for child in child_blueprint:
        child_id = str(child.get("title", "")).strip()
        if not child_id:
            continue
        if child_id in node_catalog:
            if child_id not in current_children:
                current_children.append(child_id)
            if child_id not in active_frontier and not mastery.get(child_id, False):
                active_frontier.append(child_id)
            continue

        child_kind = str(child.get("node_kind", "concept") or "concept").lower()
        if child_kind not in {"concept", "advanced"}:
            child_kind = "concept"
        math_heavy = bool(child.get("is_math_heavy", infer_math_heavy(child_id)))
        node_catalog[child_id] = build_node_meta(
            node_id=child_id,
            parent_node_id=current,
            depth=child_depth,
            node_kind=child_kind,
            is_math_heavy=math_heavy,
            parent_path=parent_path,
            is_expanded=False,
        )
        parent_map[child_id] = current
        children_map.setdefault(child_id, [])
        if child_id not in current_children:
            current_children.append(child_id)
        if child_id not in subtopics:
            subtopics.append(child_id)
        if child_id not in graph_nodes:
            graph_nodes[child_id] = {
                "status": "unlocked",
                "attempts": 0,
                "best_score": 0.0,
            }
        if child_id not in active_frontier and not mastery.get(child_id, False):
            active_frontier.append(child_id)

    children_map[current] = current_children
    current_meta["is_expanded"] = True
    node_catalog[current] = current_meta
    if current not in expanded_nodes:
        expanded_nodes.append(current)

    active_frontier = [node for node in active_frontier if node != current]
    return (
        subtopics,
        graph_nodes,
        node_catalog,
        parent_map,
        children_map,
        expanded_nodes,
        active_frontier,
    )


def _find_bridge_parent(history: list[dict[str, Any]], bridge_topic: str) -> str | None:
    for entry in reversed(history):
        if entry.get("type") == "bridge" and entry.get("bridge_topic") == bridge_topic:
            return entry.get("parent_subtopic")
    return None
