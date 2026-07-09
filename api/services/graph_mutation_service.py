"""
Graph node CRUD — add, delete, and expand operations on the learning tree.

Each builder function computes the full set of state updates needed, which
are then applied atomically via the runner's checkpoint mechanism.
"""

from __future__ import annotations

from typing import Any

from agent.config import get_settings as get_agent_settings
from agent.nodes._tree import (
    build_node_meta,
    infer_math_heavy,
    generate_child_blueprint,
)
from api.schemas.learning import GraphNodeCreateRequest
from api.services.graph_helpers import (
    normalize_node_list,
    normalize_children_map,
    safe_int,
)
from api.services.lesson_service import (
    build_starter_lesson_payload,
    append_lesson_entries,
)

_GRAPH_HISTORY_LIMIT = 300


# ── Add node ──────────────────────────────────────────────────


def build_add_node_updates(
    values: dict[str, Any], payload: GraphNodeCreateRequest
) -> tuple[dict[str, Any], str]:
    """Compute state updates that insert a new node under a parent."""
    node_id = str(payload.node_id or "").strip()
    if not node_id:
        raise ValueError("node_id cannot be empty.")

    node_catalog = values.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}
    graph_nodes = values.get("graph_nodes", {})
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    subtopics = normalize_node_list(values.get("subtopics", []))

    if node_id in node_catalog or node_id in graph_nodes or node_id in subtopics:
        raise ValueError(f"Node '{node_id}' already exists in this session.")

    current_node = str(values.get("current_node", "") or "").strip()
    parent_node_id = str(payload.parent_node_id or "").strip() or current_node
    if not parent_node_id:
        raise ValueError("parent_node_id is required when current_node is unavailable.")
    if parent_node_id not in node_catalog:
        raise ValueError(f"Parent node '{parent_node_id}' was not found.")

    parent_meta = node_catalog.get(parent_node_id, {})
    if not isinstance(parent_meta, dict):
        parent_meta = {}
    parent_depth = safe_int(parent_meta.get("depth", 0), 0)
    parent_path = parent_meta.get("path_from_root", [parent_node_id])
    if not isinstance(parent_path, list) or not parent_path:
        parent_path = [parent_node_id]

    inferred_math = infer_math_heavy(node_id) or bool(
        parent_meta.get("is_math_heavy", False)
    )
    node_meta = build_node_meta(
        node_id=node_id,
        parent_node_id=parent_node_id,
        depth=parent_depth + 1,
        node_kind=payload.node_kind,
        is_math_heavy=(
            bool(payload.is_math_heavy)
            if payload.is_math_heavy is not None
            else inferred_math
        ),
        parent_path=[str(p).strip() for p in parent_path if str(p).strip()],
        is_expanded=False,
    )

    # Build output copies
    node_catalog_out = dict(node_catalog)
    node_catalog_out[node_id] = node_meta
    graph_nodes_out = dict(graph_nodes)
    graph_nodes_out[node_id] = {"status": "unlocked", "attempts": 0, "best_score": 0.0}
    subtopics_out = list(subtopics)
    subtopics_out.append(node_id)

    parent_map = values.get("parent_map", {})
    if not isinstance(parent_map, dict):
        parent_map = {}
    parent_map_out = dict(parent_map)
    parent_map_out[node_id] = parent_node_id

    children_map_out = normalize_children_map(values.get("children_map", {}))
    parent_children = list(children_map_out.get(parent_node_id, []))
    if node_id not in parent_children:
        parent_children.append(node_id)
    children_map_out[parent_node_id] = parent_children
    children_map_out.setdefault(node_id, [])

    active_frontier_out = normalize_node_list(values.get("active_frontier", []))
    available_choices_out = normalize_node_list(values.get("available_choices", []))
    if payload.add_to_frontier:
        if node_id not in active_frontier_out:
            active_frontier_out.append(node_id)
        if node_id not in available_choices_out:
            available_choices_out.append(node_id)

    mastery = values.get("mastery", {})
    if not isinstance(mastery, dict):
        mastery = {}
    mastery_out = dict(mastery)
    mastery_out[node_id] = False

    weak_areas = values.get("weak_areas", {})
    if not isinstance(weak_areas, dict):
        weak_areas = {}
    weak_areas_out = dict(weak_areas)
    weak_areas_out[node_id] = []

    history = values.get("history", [])
    if not isinstance(history, list):
        history = []
    history_out = list(history)
    history_out.append(
        {
            "type": "graph_add_node",
            "node_id": node_id,
            "parent_node_id": parent_node_id,
            "node_kind": payload.node_kind,
            "add_to_frontier": bool(payload.add_to_frontier),
        }
    )

    lesson_payload = build_starter_lesson_payload(
        topic=str(values.get("topic", "") or ""),
        node_id=node_id,
        parent_node_id=parent_node_id,
        node_kind=payload.node_kind,
        is_math_heavy=bool(node_meta.get("is_math_heavy", False)),
    )
    history_out = append_lesson_entries(
        history_out,
        target_node=node_id,
        lesson_payload=lesson_payload,
        source="graph_add_starter",
    )

    return (
        {
            "node_catalog": node_catalog_out,
            "graph_nodes": graph_nodes_out,
            "subtopics": subtopics_out,
            "parent_map": parent_map_out,
            "children_map": children_map_out,
            "active_frontier": active_frontier_out,
            "available_choices": available_choices_out,
            "mastery": mastery_out,
            "weak_areas": weak_areas_out,
            "history": history_out,
        },
        node_id,
    )


# ── Expand node ───────────────────────────────────────────────


async def build_expand_node_updates(
    values: dict[str, Any], *, node_id: str
) -> tuple[dict[str, Any], list[str]]:
    """Generate children via LLM and compute state updates that attach them."""
    target = str(node_id or "").strip()
    if not target:
        raise ValueError("node_id cannot be empty.")

    node_catalog = values.get("node_catalog", {})
    if not isinstance(node_catalog, dict) or target not in node_catalog:
        raise ValueError(f"Node '{target}' was not found in this session.")

    parent_meta = node_catalog.get(target, {})
    if not isinstance(parent_meta, dict):
        parent_meta = {}
    if (
        str(parent_meta.get("node_kind", "concept") or "concept").lower()
        == "remediation"
    ):
        raise ValueError("Remediation nodes cannot be manually expanded.")

    children_map = normalize_children_map(values.get("children_map", {}))
    existing_children = list(children_map.get(target, []))

    settings = get_agent_settings()
    topic = str(values.get("topic", "") or "")
    course_mode = str(values.get("course_mode", "detailed") or "detailed")
    parent_depth = safe_int(parent_meta.get("depth", 0), 0)
    weak_areas_map = values.get("weak_areas", {})
    if not isinstance(weak_areas_map, dict):
        weak_areas_map = {}
    weak_areas = weak_areas_map.get(target, [])
    if not isinstance(weak_areas, list):
        weak_areas = []

    existing_titles = {str(k).strip().lower() for k in node_catalog.keys()}
    existing_titles.update(
        str(st).strip().lower()
        for st in normalize_node_list(values.get("subtopics", []))
    )

    child_blueprint = await generate_child_blueprint(
        topic=topic,
        parent_node=target,
        parent_depth=parent_depth,
        weak_areas=weak_areas,
        min_children=max(1, int(settings.tree_min_children)),
        max_children=max(
            int(settings.tree_min_children), int(settings.tree_max_children)
        ),
        course_mode=course_mode,
        existing_titles=existing_titles,
    )
    if not isinstance(child_blueprint, list):
        child_blueprint = []

    # Prepare output copies
    graph_nodes = values.get("graph_nodes", {})
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    parent_map = values.get("parent_map", {})
    if not isinstance(parent_map, dict):
        parent_map = {}
    subtopics = normalize_node_list(values.get("subtopics", []))
    active_frontier = normalize_node_list(values.get("active_frontier", []))
    available_choices = normalize_node_list(values.get("available_choices", []))
    mastery = values.get("mastery", {})
    if not isinstance(mastery, dict):
        mastery = {}
    weak_areas_out = dict(weak_areas_map)
    expanded_nodes = normalize_node_list(values.get("expanded_nodes", []))
    parent_path = parent_meta.get("path_from_root", [target])
    if not isinstance(parent_path, list) or not parent_path:
        parent_path = [target]

    node_catalog_out = dict(node_catalog)
    graph_nodes_out = dict(graph_nodes)
    parent_map_out = dict(parent_map)
    children_map_out = dict(children_map)
    subtopics_out = list(subtopics)
    active_frontier_out = list(active_frontier)
    available_choices_out = list(available_choices)
    mastery_out = dict(mastery)
    expanded_nodes_out = list(expanded_nodes)
    added_node_ids: list[str] = []

    history = values.get("history", [])
    if not isinstance(history, list):
        history = []
    history_out = list(history)

    for item in child_blueprint:
        if not isinstance(item, dict):
            continue
        child_id = str(item.get("title", "")).strip()
        if not child_id or child_id in node_catalog_out:
            continue

        child_kind = str(item.get("node_kind", "concept") or "concept").lower()
        if child_kind not in {"concept", "advanced"}:
            child_kind = "concept"
        child_math = bool(item.get("is_math_heavy", infer_math_heavy(child_id)))

        child_meta = build_node_meta(
            node_id=child_id,
            parent_node_id=target,
            depth=parent_depth + 1,
            node_kind=child_kind,
            is_math_heavy=child_math,
            parent_path=[str(p).strip() for p in parent_path if str(p).strip()],
            is_expanded=False,
        )
        node_catalog_out[child_id] = child_meta
        graph_nodes_out[child_id] = {
            "status": "unlocked",
            "attempts": 0,
            "best_score": 0.0,
        }
        parent_map_out[child_id] = target
        children_map_out.setdefault(child_id, [])
        if child_id not in subtopics_out:
            subtopics_out.append(child_id)
        if child_id not in active_frontier_out:
            active_frontier_out.append(child_id)
        if child_id not in available_choices_out:
            available_choices_out.append(child_id)
        mastery_out[child_id] = False
        weak_areas_out[child_id] = []
        added_node_ids.append(child_id)

        starter = build_starter_lesson_payload(
            topic=topic,
            node_id=child_id,
            parent_node_id=target,
            node_kind=child_kind,
            is_math_heavy=child_math,
        )
        history_out = append_lesson_entries(
            history_out,
            target_node=child_id,
            lesson_payload=starter,
            source="graph_expand_starter",
        )

    merged_children = list(existing_children)
    for child in added_node_ids:
        if child not in merged_children:
            merged_children.append(child)
    children_map_out[target] = merged_children

    parent_meta_out = dict(node_catalog_out.get(target, {}))
    parent_meta_out["is_expanded"] = True
    node_catalog_out[target] = parent_meta_out
    if target not in expanded_nodes_out:
        expanded_nodes_out.append(target)

    history_out.append(
        {
            "type": "graph_expand_node",
            "node_id": target,
            "children_added": list(added_node_ids),
        }
    )
    history_out = history_out[-_GRAPH_HISTORY_LIMIT:]

    return (
        {
            "node_catalog": node_catalog_out,
            "graph_nodes": graph_nodes_out,
            "parent_map": parent_map_out,
            "children_map": children_map_out,
            "subtopics": subtopics_out,
            "active_frontier": active_frontier_out,
            "available_choices": available_choices_out,
            "mastery": mastery_out,
            "weak_areas": weak_areas_out,
            "expanded_nodes": expanded_nodes_out,
            "history": history_out,
        },
        added_node_ids,
    )


# ── Delete node ───────────────────────────────────────────────


def build_delete_node_updates(
    values: dict[str, Any], *, node_id: str, cascade: bool
) -> tuple[dict[str, Any], list[str]]:
    """Compute state updates that remove a node (and optionally its subtree)."""
    target = str(node_id or "").strip()
    if not target:
        raise ValueError("node_id cannot be empty.")

    node_catalog = values.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}
    graph_nodes = values.get("graph_nodes", {})
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    subtopics = normalize_node_list(values.get("subtopics", []))

    known_nodes = set(node_catalog.keys()) | set(graph_nodes.keys()) | set(subtopics)
    if target not in known_nodes:
        raise ValueError(f"Node '{target}' was not found in this session.")

    parent_map = values.get("parent_map", {})
    if not isinstance(parent_map, dict):
        parent_map = {}
    parent_node_id = parent_map.get(target)
    if parent_node_id is None and isinstance(node_catalog.get(target), dict):
        parent_node_id = node_catalog.get(target, {}).get("parent_node_id")
    if parent_node_id is None:
        raise ValueError("Cannot delete the root node.")

    current_node = str(values.get("current_node", "") or "").strip()
    if target == current_node:
        raise ValueError("Cannot delete the currently active node.")

    children_map = normalize_children_map(values.get("children_map", {}))
    if list(children_map.get(target, [])) and not cascade:
        raise ValueError("Node has children. Set cascade=true to delete the subtree.")

    removed_nodes = (
        _collect_subtree_nodes(target, children_map) if cascade else [target]
    )
    removed_set = set(removed_nodes)
    if current_node and current_node in removed_set:
        raise ValueError(
            "Cannot delete a subtree that contains the currently active node."
        )

    # Purge removed nodes from every state container
    node_catalog_out = {k: v for k, v in node_catalog.items() if k not in removed_set}
    graph_nodes_out = {k: v for k, v in graph_nodes.items() if k not in removed_set}
    parent_map_out = {k: v for k, v in parent_map.items() if k not in removed_set}
    children_map_out = {
        parent: [c for c in children if c not in removed_set]
        for parent, children in children_map.items()
        if parent not in removed_set
    }
    subtopics_out = [n for n in subtopics if n not in removed_set]
    active_frontier_out = [
        n
        for n in normalize_node_list(values.get("active_frontier", []))
        if n not in removed_set
    ]
    available_choices_out = [
        n
        for n in normalize_node_list(values.get("available_choices", []))
        if n not in removed_set
    ]
    expanded_nodes_out = [
        n
        for n in normalize_node_list(values.get("expanded_nodes", []))
        if n not in removed_set
    ]

    mastery = values.get("mastery", {})
    mastery_out = {
        k: v
        for k, v in (mastery if isinstance(mastery, dict) else {}).items()
        if k not in removed_set
    }
    scores = values.get("scores", {})
    scores_out = {
        k: v
        for k, v in (scores if isinstance(scores, dict) else {}).items()
        if k not in removed_set
    }
    weak_areas = values.get("weak_areas", {})
    weak_areas_out = {
        k: v
        for k, v in (weak_areas if isinstance(weak_areas, dict) else {}).items()
        if k not in removed_set
    }

    navigation_stack = [
        n
        for n in normalize_node_list(values.get("navigation_stack", []))
        if n not in removed_set
    ]
    if current_node and not navigation_stack:
        navigation_stack = [current_node]

    selected_next_node = str(values.get("selected_next_node", "") or "").strip()
    if selected_next_node in removed_set:
        selected_next_node = ""

    current_path = normalize_node_list(values.get("current_path", []))
    if any(n in removed_set for n in current_path):
        meta = node_catalog_out.get(current_node, {})
        replacement = meta.get("path_from_root", [current_node] if current_node else [])
        if not isinstance(replacement, list):
            replacement = [current_node] if current_node else []
        current_path = [str(n).strip() for n in replacement if str(n).strip()]

    history = values.get("history", [])
    if not isinstance(history, list):
        history = []
    history_out = list(history)
    history_out.append(
        {
            "type": "graph_delete_node",
            "node_id": target,
            "cascade": bool(cascade),
            "removed_nodes": list(removed_nodes),
        }
    )
    history_out = history_out[-_GRAPH_HISTORY_LIMIT:]

    return (
        {
            "node_catalog": node_catalog_out,
            "graph_nodes": graph_nodes_out,
            "parent_map": parent_map_out,
            "children_map": children_map_out,
            "subtopics": subtopics_out,
            "active_frontier": active_frontier_out,
            "available_choices": available_choices_out,
            "expanded_nodes": expanded_nodes_out,
            "mastery": mastery_out,
            "scores": scores_out,
            "weak_areas": weak_areas_out,
            "navigation_stack": navigation_stack,
            "selected_next_node": selected_next_node,
            "current_path": current_path,
            "history": history_out,
        },
        removed_nodes,
    )


# ── Tree traversal ────────────────────────────────────────────


def _collect_subtree_nodes(
    root_node: str, children_map: dict[str, list[str]]
) -> list[str]:
    """DFS-collect all nodes in the subtree rooted at *root_node*."""
    out: list[str] = []
    seen: set[str] = set()
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        out.append(node)
        for child in reversed(children_map.get(node, [])):
            child_id = str(child).strip()
            if child_id and child_id not in seen:
                stack.append(child_id)
    return out
