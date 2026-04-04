"""
next_node_generator — Advance through a choice-based learning frontier.

The learner can explicitly select the next node from available choices.
If no explicit selection is provided, we fall back to traversal_mode:
- bfs: earliest remaining node
- dfs: latest remaining node
"""

from __future__ import annotations

from typing import Any

from agent.state import CognimapState


async def next_node_generator(state: CognimapState) -> dict[str, Any]:
    """Mark progress and choose the next node from the remaining frontier."""
    current = state["current_node"]
    subtopics = list(state.get("subtopics", []))
    graph_nodes = dict(state.get("graph_nodes", {}))
    node_catalog = dict(state.get("node_catalog", {}))
    mastery = dict(state.get("mastery", {}))
    history = list(state.get("history", []))
    navigation_stack = list(state.get("navigation_stack", []))
    active_frontier = list(state.get("active_frontier", []))
    selected = str(state.get("selected_next_node", "") or "").strip()
    traversal_mode = str(state.get("traversal_mode", "dfs") or "dfs").lower()
    journey_mode = str(state.get("journey_mode", "learn") or "learn").lower()
    if traversal_mode not in {"bfs", "dfs"}:
        traversal_mode = "dfs"
    if journey_mode not in {"learn", "review"}:
        journey_mode = "learn"

    if not navigation_stack:
        navigation_stack = [current]
    elif navigation_stack[-1] != current:
        navigation_stack.append(current)
    previous_node = navigation_stack[-2] if len(navigation_stack) >= 2 else None

    # Passing a remediation node should also master its parent subtopic.
    parent_subtopic = _find_bridge_parent(history, current) if current not in subtopics else None
    mastery[current] = True
    if parent_subtopic:
        mastery[parent_subtopic] = True

    if current in graph_nodes:
        node_meta = dict(graph_nodes[current])
        node_meta["status"] = "mastered"
        graph_nodes[current] = node_meta
    if parent_subtopic and parent_subtopic in graph_nodes:
        parent_meta = dict(graph_nodes[parent_subtopic])
        parent_meta["status"] = "mastered"
        graph_nodes[parent_subtopic] = parent_meta

    active_frontier = [node for node in active_frontier if node != current and not mastery.get(node, False)]
    remaining = [st for st in subtopics if not mastery.get(st, False) and st != current]
    for node in remaining:
        if node not in active_frontier:
            active_frontier.append(node)

    is_backtrack = bool(selected and previous_node and selected == previous_node)
    if is_backtrack:
        next_subtopic = previous_node
    elif selected and selected in subtopics and selected != current:
        next_subtopic = selected
    elif active_frontier:
        next_subtopic = active_frontier[0] if traversal_mode == "bfs" else active_frontier[-1]
    else:
        next_subtopic = current

    active_frontier = [node for node in active_frontier if node != next_subtopic]

    if is_backtrack:
        journey_mode = "review"
        if navigation_stack and navigation_stack[-1] == current:
            navigation_stack.pop()
    elif next_subtopic != current:
        if mastery.get(next_subtopic, False):
            journey_mode = "review"
        else:
            journey_mode = "learn"
        if not navigation_stack or navigation_stack[-1] != next_subtopic:
            navigation_stack.append(next_subtopic)

    available_choices = [st for st in active_frontier if st != next_subtopic and not mastery.get(st, False)]

    current_meta = node_catalog.get(next_subtopic, {})
    current_path = current_meta.get("path_from_root", [next_subtopic])
    if not isinstance(current_path, list) or not current_path:
        current_path = [next_subtopic]

    for st in subtopics:
        if st in graph_nodes:
            meta = dict(graph_nodes[st])
            if mastery.get(st, False):
                meta["status"] = "mastered"
            else:
                meta["status"] = "unlocked"
            graph_nodes[st] = meta

    if next_subtopic != current:
        history.append({
            "type": "transition",
            "from_node": current,
            "to_node": next_subtopic,
            "journey_mode": journey_mode,
            "backtrack": is_backtrack,
        })

    return {
        "current_node": next_subtopic,
        "graph_nodes": graph_nodes,
        "mastery": mastery,
        "node_catalog": node_catalog,
        "active_frontier": active_frontier,
        "current_path": current_path,
        "available_choices": available_choices,
        "selected_next_node": "",
        "traversal_mode": traversal_mode,
        "navigation_stack": navigation_stack,
        "journey_mode": journey_mode,
        "history": history,
        "remediation_count": 0,
        "lesson": {},
        "evaluation": {},
    }


def _find_bridge_parent(history: list[dict], bridge_topic: str) -> str | None:
    """Walk history backwards to find the parent_subtopic for a bridge topic."""
    for entry in reversed(history):
        if entry.get("type") == "bridge" and entry.get("bridge_topic") == bridge_topic:
            return entry.get("parent_subtopic")
    return None
