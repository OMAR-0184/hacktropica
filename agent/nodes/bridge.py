"""
bridge_node_generator — Creates a remediation micro-topic from weak areas.
"""

from __future__ import annotations

import json
from typing import Any

from agent.nodes._llm_call import invoke_llm_json
from agent.state import CognimapState

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

    bridge_topic = bridge_data.get("bridge_topic", f"Remediation: {current}")

    graph_nodes = dict(state.get("graph_nodes", {}))
    graph_nodes[bridge_topic] = {
        "status": "unlocked",
        "attempts": 0,
        "best_score": 0.0,
    }

    history = list(state.get("history", []))
    history.append({
        "type": "bridge",
        "parent_subtopic": current,
        "bridge_topic": bridge_topic,
        "focus_areas": bridge_data.get("focus_areas", weak),
    })

    remediation_count = state.get("remediation_count", 0) + 1

    return {
        "current_node": bridge_topic,
        "graph_nodes": graph_nodes,
        "history": history,
        "remediation_count": remediation_count,
        "lesson": {},
        "evaluation": {},
    }
