"""
router_node — Decision engine that determines the next path.

This is a pure routing function (no LLM call). It returns a string
used by LangGraph's conditional_edges to pick the next node.
"""

from __future__ import annotations

from agent.config import get_settings
from agent.nodes._mcq import determine_next_action
from agent.state import CognimapState


def router_node(state: CognimapState) -> str:
    """
    Route based on score and remediation count.

    Returns one of:
        "next"  — advance to the next subtopic
        "bridge" — create a remediation micro-topic
        "__end__" — all subtopics mastered, finish
    """
    settings = get_settings()
    current = state["current_node"]
    score = state.get("scores", {}).get(current, 0.0)
    remediation_count = state.get("remediation_count", 0)
    action = determine_next_action(
        passed=score >= settings.mastery_threshold,
        current_node=current,
        subtopics=list(state.get("subtopics", [])),
        remediation_count=remediation_count,
        max_remediation=settings.max_remediation,
        history=list(state.get("history", [])),
        mastery=dict(state.get("mastery", {})),
    )

    if action == "remediation":
        return "bridge"
    if action == "next_topic":
        return "next"
    return "__end__"
