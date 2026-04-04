"""
quiz_node — Generates a short quiz based on the lesson content.
Runs immediately after lesson generation, directly prior to the graph interrupt.
"""

from __future__ import annotations

from typing import Any

from agent.nodes._mcq import compute_numerical_ratio, normalize_mcq_questions
from agent.nodes._llm_call import invoke_llm_json
from agent.nodes._tree import determine_quiz_profile
from agent.state import CognimapState

_SYSTEM_PROMPT = """\
You are an expert instructional designer creating a deterministic MCQ quiz from lesson content.
Design exactly {question_count} higher-order multiple-choice questions. Each question must have exactly 4 options and exactly one correct option.
Avoid trivial definitions; focus on application, analysis, and decision-making scenarios.
If numerical_target_ratio is greater than 0, ensure at least that fraction of questions are numerical/calculation/application problems.
Do not use placeholders, gibberish, or meta text. Never use "Option A/B/C/D", "All of the above", or "None of the above".
Each question and option set must be self-contained, factually coherent, and directly tied to the provided subtopic and lesson details.
Distractors should be plausible but clearly incorrect based on the lesson content.

Return ONLY valid JSON with this shape:
{
  "questions": [
    {
      "question_id": "q1",
      "question": "question text",
      "options": ["A", "B", "C", "D"],
      "correct_index": 0,
      "concept": "short concept label"
    }
  ]
}
"""

_DEFAULTS = {"questions": []}


def _build_system_prompt(question_count: int) -> str:
    """Safely inject question count without interpreting JSON braces."""
    return _SYSTEM_PROMPT.replace("{question_count}", str(int(question_count)))


def _build_lesson_context(tutor_content: Any) -> str:
    if not isinstance(tutor_content, dict):
        return "No lesson content available."

    objective = str(tutor_content.get("learning_objective") or "").strip()
    explanation = str(tutor_content.get("explanation") or "").strip()
    misconception = str(tutor_content.get("common_misconception") or "").strip()
    practice_task = str(tutor_content.get("practice_task") or "").strip()

    raw_examples = tutor_content.get("examples")
    examples: list[str] = []
    if isinstance(raw_examples, list):
        for ex in raw_examples[:3]:
            value = str(ex).strip()
            if value:
                examples.append(value)

    lines = [
        f"Learning objective: {objective or 'N/A'}",
        f"Explanation: {explanation[:1200] or 'N/A'}",
        "Examples:",
    ]
    if examples:
        lines.extend(f"- {ex}" for ex in examples)
    else:
        lines.append("- N/A")
    lines.extend(
        [
            f"Common misconception: {misconception or 'N/A'}",
            f"Practice task: {practice_task or 'N/A'}",
        ]
    )
    return "\n".join(lines)


async def quiz_node(state: CognimapState) -> dict[str, Any]:
    """Generate quiz questions and answers for the current lesson."""
    current = state["current_node"]
    lesson = state.get("lesson", {})
    node_catalog = state.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}
    node_meta = node_catalog.get(current, {})
    if not isinstance(node_meta, dict):
        node_meta = {}
    question_count, numerical_target_ratio = determine_quiz_profile(node_meta, current)

    lesson_summary = _build_lesson_context(lesson.get("tutor_content", {}))

    quiz = await invoke_llm_json(
        node_type="evaluator",  # Re-use evaluator LLM config
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": _build_system_prompt(question_count),
            },
            {
                "role": "user",
                "content": (
                    f"Subtopic: {current}\n\n"
                    f"Lesson content:\n{lesson_summary}\n\n"
                    f"question_count: {question_count}\n"
                    f"numerical_target_ratio: {numerical_target_ratio}\n\n"
                    "Create questions that can be answered from this lesson content. "
                    "If detail is missing, use conservative, fundamentals-based scenarios tied to the same subtopic."
                ),
            },
        ],
        required_keys=["questions"],
        defaults=_DEFAULTS,
    )

    questions = normalize_mcq_questions(
        quiz.get("questions"),
        current,
        expected_count=question_count,
        numerical_target_ratio=numerical_target_ratio,
    )
    actual_numerical_ratio = compute_numerical_ratio(questions)
    return {
        "quiz": {
            "questions": questions,
            "question_count": question_count,
            "numerical_target_ratio": numerical_target_ratio,
            "actual_numerical_ratio": actual_numerical_ratio,
        }
    }
