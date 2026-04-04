from __future__ import annotations

from typing import Any

from agent.state import CognimapState

_HISTORY_LIMIT = 300


async def merge_node(state: CognimapState) -> dict[str, Any]:
    """Merge tutor and curator content into a unified lesson."""
    lesson = dict(state.get("lesson", {}))
    current = state["current_node"]

    lesson["subtopic"] = current

    history = list(state.get("history", []))
    history.append({"type": "lesson", "subtopic": current, "lesson": lesson})
    history = history[-_HISTORY_LIMIT:]

    return {"lesson": lesson, "history": history}
