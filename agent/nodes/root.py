"""
root_node — Initializes a parent-first hierarchy rooted at Intro to <Topic>.
"""

from __future__ import annotations

from typing import Any

from agent.nodes._tree import build_node_meta, infer_math_heavy
from agent.state import CognimapState

async def root_node(state: CognimapState) -> dict[str, Any]:
    """Create canonical intro parent node and initialize traversal metadata."""
    topic = state["topic"]
    course_mode = state.get("course_mode", "detailed")
    traversal_mode = str(state.get("traversal_mode", "dfs") or "dfs").strip().lower()
    if traversal_mode not in {"bfs", "dfs"}:
        traversal_mode = "dfs"
    intro_node = f"Intro to {str(topic).strip()}"
    topic_math_heavy = infer_math_heavy(topic)
    graph_nodes = {
        intro_node: {
            "status": "unlocked",
            "attempts": 0,
            "best_score": 0.0,
        }
    }
    node_catalog = {
        intro_node: build_node_meta(
            node_id=intro_node,
            parent_node_id=None,
            depth=0,
            node_kind="intro",
            is_math_heavy=topic_math_heavy,
            parent_path=[],
            is_expanded=False,
        )
    }

    return {
        "subtopics": [intro_node],
        "current_node": intro_node,
        "node_catalog": node_catalog,
        "parent_map": {intro_node: None},
        "children_map": {intro_node: []},
        "expanded_nodes": [],
        "active_frontier": [],
        "current_path": [intro_node],
        "available_choices": [],
        "selected_next_node": "",
        "traversal_mode": traversal_mode,
        "navigation_stack": [intro_node],
        "journey_mode": "learn",
        "journey_orchestrator_v2": bool(state.get("journey_orchestrator_v2", False)),
        "course_mode": course_mode,
        "learner_profile": state.get("learner_profile", ""),
        "graph_nodes": graph_nodes,
        "history": [],
        "scores": {},
        "weak_areas": {},
        "mastery": {},
        "lesson": {},
        "evaluation": {},
        "remediation_count": 0,
    }
