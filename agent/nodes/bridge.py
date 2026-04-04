"""
bridge_node_generator — Creates a remediation micro-topic from weak areas.
"""

from __future__ import annotations

import json
from typing import Any

from agent.nodes._llm_call import invoke_llm_json
from agent.nodes._tree import build_node_meta, infer_math_heavy
from agent.state import CognimapState

_HISTORY_LIMIT = 300

_SYSTEM_PROMPT = """\
You are a learning remediation specialist. A learner struggled with certain
concepts within a subtopic. Create a focused micro-lesson to address the weak
areas. Return ONLY a JSON object with these keys:
- "bridge_topic": a short title for the remediation micro-topic
- "focus_areas": list of specific concepts being remediated
"""


async def bridge_node_generator(state: CognimapState) -> dict[str, Any]:
    """Generate a remediation micro-topic and insert it into the graph."""
    current = state["current_node"]
    weak = state.get("weak_areas", {}).get(current, [])
    topic = state.get("topic", "")

    bridge_data = await invoke_llm_json(
        node_type="bridge",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Broader topic: {topic}\n"
                    f"Subtopic: {current}\n"
                    f"Weak areas: {json.dumps(weak)}"
                ),
            },
        ],
        required_keys=["bridge_topic", "focus_areas"],
        defaults={
            "bridge_topic": f"Remediation: {current}",
            "focus_areas": weak if weak else ["General review"],
        },
    )

    bridge_topic = str(bridge_data.get("bridge_topic", f"Remediation: {current}") or "").strip()

    graph_nodes = dict(state.get("graph_nodes", {}))
    node_catalog = dict(state.get("node_catalog", {}))
    parent_map = dict(state.get("parent_map", {}))
    children_map = dict(state.get("children_map", {}))
    active_frontier = list(state.get("active_frontier", []))
    existing_ids = {str(node).strip() for node in node_catalog.keys()}
    existing_ids.update(str(node).strip() for node in graph_nodes.keys())
    existing_ids.update(str(node).strip() for node in state.get("subtopics", []))
    bridge_topic = _ensure_unique_bridge_topic(
        bridge_topic or f"Remediation: {current}",
        existing_ids=existing_ids,
    )

    graph_nodes[bridge_topic] = {
        "status": "unlocked",
        "attempts": 0,
        "best_score": 0.0,
    }

    parent_meta = node_catalog.get(current, {})
    parent_depth = int(parent_meta.get("depth", 0))
    parent_path = parent_meta.get("path_from_root", [current])
    if not isinstance(parent_path, list) or not parent_path:
        parent_path = [current]
    node_catalog[bridge_topic] = build_node_meta(
        node_id=bridge_topic,
        parent_node_id=current,
        depth=parent_depth + 1,
        node_kind="remediation",
        is_math_heavy=bool(parent_meta.get("is_math_heavy", infer_math_heavy(current))),
        parent_path=parent_path,
        is_expanded=True,
    )
    parent_map[bridge_topic] = current
    parent_children = list(children_map.get(current, []))
    if bridge_topic not in parent_children:
        parent_children.append(bridge_topic)
    children_map[current] = parent_children
    children_map.setdefault(bridge_topic, [])
    active_frontier = [node for node in active_frontier if node != bridge_topic]

    history = list(state.get("history", []))
    history.append({
        "type": "bridge",
        "parent_subtopic": current,
        "bridge_topic": bridge_topic,
        "focus_areas": bridge_data.get("focus_areas", weak),
    })
    history = history[-_HISTORY_LIMIT:]

    remediation_count = state.get("remediation_count", 0) + 1
    navigation_stack = list(state.get("navigation_stack", []))
    if not navigation_stack or navigation_stack[-1] != current:
        navigation_stack.append(current)
    if navigation_stack[-1] != bridge_topic:
        navigation_stack.append(bridge_topic)
    current_path = node_catalog.get(bridge_topic, {}).get("path_from_root", [bridge_topic])
    if not isinstance(current_path, list) or not current_path:
        current_path = [bridge_topic]

    return {
        "current_node": bridge_topic,
        "graph_nodes": graph_nodes,
        "node_catalog": node_catalog,
        "parent_map": parent_map,
        "children_map": children_map,
        "active_frontier": active_frontier,
        "current_path": current_path,
        "history": history,
        "remediation_count": remediation_count,
        "navigation_stack": navigation_stack,
        "journey_mode": "learn",
        "lesson": {},
        "evaluation": {},
    }


def _ensure_unique_bridge_topic(base_topic: str, *, existing_ids: set[str]) -> str:
    seed = str(base_topic or "").strip() or "Remediation"
    if seed not in existing_ids:
        return seed
    suffix = 2
    while True:
        candidate = f"{seed} ({suffix})"
        if candidate not in existing_ids:
            return candidate
        suffix += 1
