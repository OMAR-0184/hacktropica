"""
tutor_node — Generates explanation, examples, and code for the current subtopic.
"""

from __future__ import annotations

import re
from typing import Any

from agent.nodes._llm_call import invoke_llm_json
from agent.state import CognimapState

_SYSTEM_PROMPT = """\
You are an expert tutor. Given a subtopic within a broader topic, produce a
structured lesson. Return ONLY a JSON object with these keys:
- "learning_objective": one sentence describing what the learner should be able to do
- "explanation": a clear, concise explanation (2-4 paragraphs)
- "examples": a list of 2-3 illustrative examples (strings)
- "common_misconception": one common mistake learners make on this topic, with correction
- "practice_task": one short task the learner can do right now
- "code_snippet": a relevant code snippet if applicable, otherwise null

Write in child-safe language suitable for younger learners. Do not use profanity
or unsafe content.

Quality rules:
- Be technically accurate and avoid vague placeholders.
- Avoid repetitive toy metaphors ("tiny", "special path", etc.).
- For detailed mode, prefer academically clear language with concrete terminology.
- Use examples grounded in the actual subject, not generic analogies.
- Include at least one deep explanatory thread (cause-effect, mechanism, or derivation where relevant).
- Include one practical transfer example that connects this node to what learner should study next.
- When the topic is quantitative, include equations/units/steps conceptually (and code only if genuinely useful).
"""

_DEFAULTS = {
    "learning_objective": "Understand the main concept and apply it in a simple scenario.",
    "explanation": "Content could not be generated. Please try again.",
    "examples": [],
    "common_misconception": "A common misconception could not be generated.",
    "practice_task": "Try explaining this concept in your own words with one example.",
    "code_snippet": None,
}


async def tutor_node(state: CognimapState) -> dict[str, Any]:
    """Generate teaching content for the current subtopic."""
    topic = state.get("topic", "")
    current = state["current_node"]
    learner_profile = state.get("learner_profile", "")
    course_mode = state.get("course_mode", "detailed")
    node_catalog = state.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}
    node_meta = node_catalog.get(current, {})
    if not isinstance(node_meta, dict):
        node_meta = {}
    depth = int(node_meta.get("depth", 0))
    node_kind = str(node_meta.get("node_kind", "concept") or "concept")
    path_from_root = node_meta.get("path_from_root", [current])
    if not isinstance(path_from_root, list):
        path_from_root = [current]
    is_math_heavy = bool(node_meta.get("is_math_heavy", False))

    user_prompt = (
        f"Course mode: {course_mode}\n"
        f"Broader topic: {topic}\n"
        f"Current subtopic: {current}\n"
        f"Node depth: {depth}\n"
        f"Node kind: {node_kind}\n"
        f"Path from root: {path_from_root}\n"
        f"Math-heavy node: {is_math_heavy}"
    )
    if learner_profile:
        user_prompt += f"\n\nHistorical Learner Weaknesses to explicitly address/simplify in this lesson:\n{learner_profile}"

    tutor_content = await invoke_llm_json(
        node_type="tutor",
        temperature=0.2,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        required_keys=["learning_objective", "explanation", "examples", "common_misconception", "practice_task"],
        defaults=_DEFAULTS,
    )

    if _needs_quality_retry(tutor_content, course_mode):
        retry_user_prompt = (
            f"{user_prompt}\n\n"
            "Regenerate with higher technical quality. Keep it clear, but avoid simplistic metaphors. "
            "For science topics, use accurate vocabulary and concise precision."
        )
        tutor_content = await invoke_llm_json(
            node_type="tutor",
            temperature=0.15,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": retry_user_prompt},
            ],
            required_keys=["learning_objective", "explanation", "examples", "common_misconception", "practice_task"],
            defaults=_DEFAULTS,
        )

    lesson = dict(state.get("lesson", {}))
    lesson["tutor_content"] = tutor_content

    return {"lesson": lesson}


def _needs_quality_retry(content: dict[str, Any], course_mode: str) -> bool:
    explanation = str(content.get("explanation", "")).strip()
    examples = content.get("examples", [])
    if not isinstance(examples, list):
        examples = []

    word_count = len(re.findall(r"\w+", explanation))
    lower = explanation.lower()
    bad_phrase_hits = sum(lower.count(p) for p in ("tiny", "special path", "tiny atom", "tiny ball"))

    if course_mode == "detailed":
        if word_count < 90:
            return True
        if bad_phrase_hits >= 2:
            return True
        if any("imagine" in str(ex).lower() for ex in examples):
            return True
    else:
        if word_count < 45:
            return True
        if bad_phrase_hits >= 3:
            return True

    return False
