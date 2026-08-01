import asyncio
from typing import Any

from agent.state import CognimapState
from agent.nodes.tutor import tutor_node
from agent.nodes.curator import curator_node

_HISTORY_LIMIT = 300

async def lesson_generator_node(state: CognimapState) -> dict[str, Any]:
    """Run tutor and curator in parallel, then merge their results."""
    tutor_res, curator_res = await asyncio.gather(
        tutor_node(state),
        curator_node(state)
    )
    
    current = state["current_node"]
    
    # Extract LaTeX content (generated inside tutor_node in parallel with text).
    latex_content = tutor_res.get("latex_content", {})

    lesson = {
        "subtopic": current,
        "tutor_content": tutor_res.get("tutor_content", {}),
        "curator_content": curator_res.get("curator_content", {}),
        "latex": latex_content,
    }

    history = list(state.get("history", []))
    history.append({"type": "lesson", "subtopic": current, "lesson": lesson})
    history = history[-_HISTORY_LIMIT:]

    # Since we combined them, return the merged lesson explicitly.
    return {
        "lesson": lesson, 
        "tutor_content": tutor_res.get("tutor_content", {}),
        "curator_content": curator_res.get("curator_content", {}),
        "latex_content": latex_content,
        "history": history
    }
