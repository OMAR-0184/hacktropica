from __future__ import annotations

from typing import Any

from agent.state import CognimapState


async def merge_node(state: CognimapState) -> dict[str, Any]:
    """Merge tutor and curator content into a unified lesson."""
    lesson = dict(state.get("lesson", {}))
    current = state["current_node"]

    lesson["subtopic"] = current

    history = list(state.get("history", []))
    history.append({"type": "lesson", "subtopic": current, "lesson": lesson})

    return {"lesson": lesson, "history": history}
