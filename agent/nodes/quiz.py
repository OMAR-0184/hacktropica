"""
quiz_node — Generates a short, high-quality MCQ quiz based on the lesson content.
Runs immediately after lesson generation, directly prior to the graph interrupt.

Question design principles:
  - Concise: 1-2 sentence stems, no verbose scenarios
  - Standard: aligned with Bloom's taxonomy (Remember → Evaluate)
  - Dynamic: question count adapts to topic depth and complexity
  - Clean: no trick questions, double negatives, or ambiguous phrasing
"""

from __future__ import annotations

from typing import Any

from agent.nodes._mcq import compute_numerical_ratio, normalize_mcq_questions
from agent.nodes._llm_call import invoke_llm_json
from agent.guardrails.quiz_quality import check_quiz_quality
from agent.nodes._tree import determine_quiz_profile
from agent.state import CognimapState

_SYSTEM_PROMPT = """\
You are an expert assessment designer creating a short, high-quality MCQ quiz.

Design exactly {question_count} multiple-choice questions. Each question MUST have
exactly 4 options and exactly 1 correct answer.

QUESTION QUALITY RULES:
1. Each question stem must be 1-2 sentences. Be direct and concise — no
   storytelling, no "Imagine you are..." scenarios, no unnecessary context.
2. Test exactly ONE concept per question.
3. Align questions with Bloom's Taxonomy:
   - 30% Remember/Understand: definitions, recall, basic comprehension
   - 40% Apply/Analyze: problem-solving, comparisons, cause-effect
   - 30% Evaluate/Create: judgment, design decisions, error identification
4. For numerical/calculation questions (if numerical_target_ratio > 0):
   - Use specific numbers and units
   - Show the exact calculation required
   - Options must be concrete numerical values, not descriptions

OPTION QUALITY RULES:
1. All 4 options must be plausible and distinct.
2. Options should be roughly the same length (±30%).
3. The correct answer must NOT always be the longest option.
4. Vary the position of the correct answer across questions.
5. NEVER use: "All of the above", "None of the above", "Both A and B",
   "Option A", "Option B", placeholder text, or meta-references.
6. Each option must be self-contained and grammatically consistent with the stem.

FORBIDDEN PATTERNS:
- Double negatives ("Which is NOT incorrect...")
- Trivial definitions ("X is defined as...")
- Questions answerable without reading the lesson
- Options that are obviously wrong (joke answers, absurd choices)

Return ONLY valid JSON with this shape:
{{
  "questions": [
    {{
      "question_id": "q1",
      "question": "Concise question text?",
      "options": ["Option text A", "Option text B", "Option text C", "Option text D"],
      "correct_index": 0,
      "concept": "specific concept label",
      "bloom_level": "apply"
    }}
  ]
}}
"""

_DEFAULTS = {"questions": []}


def _build_system_prompt(question_count: int) -> str:
    """Safely inject question count without interpreting JSON braces."""
    return _SYSTEM_PROMPT.replace("{question_count}", str(int(question_count)))


def _build_lesson_context(tutor_content: Any) -> str:
    if not isinstance(tutor_content, dict):
        return "No lesson content available."

    objective = str(tutor_content.get("learning_objective") or "").strip()

    # Prefer new pedagogical fields; fall back to legacy.
    explanation = str(
        tutor_content.get("core_explanation")
        or tutor_content.get("explanation")
        or ""
    ).strip()
    misconception = str(tutor_content.get("common_misconception") or "").strip()
    practice_task = str(tutor_content.get("practice_task") or "").strip()

    raw_examples = tutor_content.get("worked_examples") or tutor_content.get(
        "examples"
    )
    examples: list[str] = []
    if isinstance(raw_examples, list):
        for ex in raw_examples[:3]:
            value = str(ex).strip()
            if value:
                examples.append(value)

    # New fields.
    hook = str(tutor_content.get("hook") or "").strip()
    summary = tutor_content.get("summary")
    summary_text = ""
    if isinstance(summary, list):
        summary_text = "; ".join(str(s).strip() for s in summary if str(s).strip())

    lines = [
        f"Learning objective: {objective or 'N/A'}",
    ]
    if hook:
        lines.append(f"Hook: {hook}")
    lines.append(f"Explanation: {explanation[:1500] or 'N/A'}")
    lines.append("Worked examples:")
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
    if summary_text:
        lines.append(f"Key takeaways: {summary_text}")
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
        node_type="quiz",
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
                    "Create concise, standard questions that test understanding "
                    "of this specific lesson content. Each question must be "
                    "brief (1-2 sentences) and test exactly one concept."
                ),
            },
        ],
        required_keys=["questions"],
        defaults=_DEFAULTS,
    )

    raw_questions = quiz.get("questions", [])

    # ── Post-generation quality check ─────────────────────────
    if isinstance(raw_questions, list) and raw_questions:
        quality_issues = check_quiz_quality(raw_questions)
        if quality_issues:
            # Targeted re-generation with quality feedback.
            quiz = await invoke_llm_json(
                node_type="quiz",
                temperature=0.15,
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
                            "Your previous quiz had these quality issues:\n"
                            + "\n".join(f"- {issue}" for issue in quality_issues)
                            + "\n\nRegenerate ALL questions, fixing these issues. "
                            "Questions must be concise (1-2 sentences), test one "
                            "concept each, and have plausible distinct options."
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


