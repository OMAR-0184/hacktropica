from __future__ import annotations

from typing import Any

from agent.state import CognimapState

_HISTORY_LIMIT = 300


async def merge_node(state: CognimapState) -> dict[str, Any]:
    """Merge tutor and curator content into a unified lesson."""
    current = state["current_node"]
    tutor_content = state.get("tutor_content", {})
    curator_content = state.get("curator_content", {})

    lesson = {
        "subtopic": current,
        "tutor_content": tutor_content,
        "curator_content": curator_content,
    }

    history = list(state.get("history", []))
    history.append({"type": "lesson", "subtopic": current, "lesson": lesson})
    history = history[-_HISTORY_LIMIT:]

    return {"lesson": lesson, "history": history}
