"""
orchestrator_node — The LLM-driven "brain" of the agent.

Dynamically decides the next node to route to based on current state, mastery,
and history, transforming the learning graph from a linear pipeline to a modern,
autonomous ReAct/Supervisor loop.
"""

from __future__ import annotations

import json
from typing import Any


from agent.nodes._llm_call import invoke_llm_json
from agent.state import CognimapState


async def orchestrator_node(state: CognimapState) -> dict[str, Any]:
    """Analyze the learner's state and dynamically decide the next best action."""

    current_node = state.get("current_node", "")
    topic = state.get("topic", "")
    mastery = state.get("mastery", {})
    scores = state.get("scores", {})
    history = state.get("history", [])
    remediation_count = state.get("remediation_count", 0)
    weak_areas = state.get("weak_areas", {})

    # Check if the current node is already fully mastered
    is_mastered = mastery.get(current_node, False)
    current_score = scores.get(current_node, 0.0)

    # Check recent history for context
    recent_history = history[-5:] if history else []

    # If a node was explicitly selected by the user (from Next action),
    # the orchestrator should usually initialize it with a lesson.
    selected_next = state.get("selected_next_node")
    if selected_next and selected_next != current_node:
        # The transition logic to `selected_next` is typically handled by `next_node`.
        pass

    prompt = (
        "You are the Orchestrator (Supervisor) of an adaptive learning curriculum.\n"
        "Your job is to look at the learner's current state and decide the single best next step.\n\n"
        f"Topic: {topic}\n"
        f"Current Node: {current_node}\n"
        f"Mastery of Current Node: {is_mastered} (Score: {current_score})\n"
        f"Remediation Count on Current Node: {remediation_count}\n"
        f"Weak Areas: {weak_areas.get(current_node, [])}\n"
        f"Recent History: {json.dumps(recent_history)}\n\n"
        "Available Actions (Next Node):\n"
        "- 'lesson_generator': Generate a comprehensive lesson and curate resources for the current node.\n"
        "- 'quiz': Generate a quiz to test knowledge of the current node.\n"
        "- 'evaluator': Grade a recently submitted quiz.\n"
        "- 'bridge': Create a remediation bridge topic if the learner is struggling.\n"
        "- 'next': Advance to the next topic in the curriculum frontier.\n\n"
        "Rules:\n"
        "1. If there is a pending 'evaluation' (quiz submitted but not graded), you MUST choose 'evaluator'.\n"
        "2. If the current node is newly visited and has no lesson, choose 'lesson_generator'.\n"
        "3. If the learner just read a lesson, choose 'quiz' to test them.\n"
        "4. If the learner failed the quiz (score < threshold) and needs help, choose 'bridge'.\n"
        "5. If the learner mastered the current node, choose 'next'.\n"
        "Return a JSON object with 'reasoning' (str) and 'next_action' (str matching one of the exact actions above)."
    )

    # Fast heuristics to save LLM calls on obvious steps
    evaluation = state.get("evaluation", {})
    lesson = state.get("lesson", {})
    quiz = state.get("quiz", {})

    if evaluation and "user_answers" in evaluation and "score" not in evaluation:
        decision = "evaluator"
        reasoning = "User submitted quiz answers; routing to evaluator for grading."
    elif is_mastered and current_node != "Intro to":
        decision = "next"
        reasoning = "Current node is mastered; routing to next."
    elif not lesson:
        decision = "lesson_generator"
        reasoning = "New concept; routing to lesson_generator to generate comprehensive lesson content."
    else:
        # Fallback to LLM for complex state resolution (e.g. after evaluation)
        try:
            res = await invoke_llm_json(
                node_type="orchestrator",
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": 'You are a routing orchestrator. Output valid JSON only: {"reasoning": "...", "next_action": "..."}',
                    },
                    {"role": "user", "content": prompt},
                ],
                required_keys=["next_action", "reasoning"],
                defaults={"next_action": "next", "reasoning": "Fallback routing."},
            )
            decision = res.get("next_action")
            reasoning = res.get("reasoning")
        except Exception as e:
            decision = "next" if is_mastered else "tutor"
            reasoning = f"Fallback due to LLM error: {str(e)}"

    valid_actions = {"lesson_generator", "quiz", "evaluator", "bridge", "next"}
    if isinstance(decision, str) and decision not in valid_actions:
        decision = "next" if is_mastered else "lesson_generator"
    elif isinstance(decision, list):
        decision = [d for d in decision if d in valid_actions]
        if not decision:
            decision = "next" if is_mastered else "lesson_generator"

    orchestrator_hist = list(state.get("orchestrator_history", []))
    orchestrator_hist.append({"decision": decision, "reasoning": reasoning})

    return {
        "orchestrator_reasoning": reasoning,
        "orchestrator_history": orchestrator_hist,
    }


def route_orchestrator(state: CognimapState) -> str | list[str]:
    """Conditional edge router based on the orchestrator's decision."""
    history = state.get("orchestrator_history", [])
    if not history:
        return "lesson_generator"

    last_decision = history[-1].get("decision", "lesson_generator")
    if isinstance(last_decision, list):
        return last_decision
    if last_decision not in {"lesson_generator", "quiz", "evaluator", "bridge", "next"}:
        return "lesson_generator"
    return last_decision
