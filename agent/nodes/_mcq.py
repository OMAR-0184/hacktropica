"""
Deterministic MCQ helpers shared by quiz, evaluator, and API layers.
"""

from __future__ import annotations

import re
from typing import Any

MCQ_COUNT = 6
MCQ_OPTION_COUNT = 4
_NUMERICAL_CUES = (
    "calculate",
    "compute",
    "solve",
    "find",
    "equation",
    "formula",
    "value",
    "numerical",
    "derive",
)
_GIBBERISH_MARKERS = (
    "lorem ipsum",
    "asdf",
    "qwerty",
    "placeholder",
    "tbd",
    "n/a",
    "blah blah",
)
_FORBIDDEN_OPTION_PHRASES = (
    "all of the above",
    "none of the above",
    "both a and b",
    "both b and c",
    "both c and d",
)


def build_fallback_questions(
    subtopic: str,
    *,
    expected_count: int = MCQ_COUNT,
    numerical_target_ratio: float = 0.0,
) -> list[dict[str, Any]]:
    """Return deterministic fallback MCQs when LLM quiz generation fails."""
    topic = subtopic or "this topic"
    expected_count = max(1, int(expected_count))
    base: list[dict[str, Any]] = [
        {
            "question_id": "q1",
            "question": f"Which option best applies the core idea of {topic} to a practical scenario?",
            "options": [
                "Select the choice that correctly applies the core concept to a real case.",
                "Choose a definition that only repeats terminology without application.",
                "Pick a statement unrelated to the scenario context.",
                "Select an answer that contradicts the key principle.",
            ],
            "correct_index": 0,
            "concept": topic,
        },
        {
            "question_id": "q2",
            "question": f"When analyzing {topic}, which approach reflects sound reasoning?",
            "options": [
                "Compare alternatives using explicit assumptions and tradeoffs.",
                "Ignore assumptions and rely only on memorized wording.",
                "Treat all alternatives as equivalent without evidence.",
                "Use circular reasoning and restate the question.",
            ],
            "correct_index": 0,
            "concept": topic,
        },
        {
            "question_id": "q3",
            "question": f"Which choice demonstrates correct evaluation of outcomes in {topic}?",
            "options": [
                "Judge outcomes against clear criteria aligned with the lesson.",
                "Pick the first option without checking the criteria.",
                "Evaluate based only on style, not correctness.",
                "Skip evaluation and assume all outcomes are valid.",
            ],
            "correct_index": 0,
            "concept": topic,
        },
    ]
    numerical_required = int(round(expected_count * max(0.0, min(1.0, numerical_target_ratio))))
    if numerical_required > 0:
        for i in range(1, numerical_required + 1):
            base.append(
                {
                    "question_id": f"qn{i}",
                    "question": f"Compute and verify the correct numerical result for {topic} case {i}.",
                    "options": [
                        f"Use the correct formula and compute the value for case {i}.",
                        f"Skip the formula and guess the result for case {i}.",
                        f"Use unrelated values that do not match case {i}.",
                        f"Choose an option with inconsistent units for case {i}.",
                    ],
                    "correct_index": 0,
                    "concept": topic,
                }
            )

    while len(base) < expected_count:
        i = len(base) + 1
        base.append(
            {
                "question_id": f"q{i}",
                "question": f"In {topic}, which option best demonstrates strong reasoning for case {i}?",
                "options": [
                    f"Apply lesson principles with clear evidence for case {i}.",
                    f"Use a guess without checking the lesson criteria for case {i}.",
                    f"Ignore the scenario constraints and pick a random method for case {i}.",
                    f"Repeat memorized wording without solving the actual problem in case {i}.",
                ],
                "correct_index": 0,
                "concept": topic,
            }
        )
    return base[:expected_count]


def normalize_mcq_questions(
    raw_questions: Any,
    subtopic: str,
    *,
    expected_count: int = MCQ_COUNT,
    numerical_target_ratio: float = 0.0,
) -> list[dict[str, Any]]:
    """Normalize arbitrary LLM JSON into strict MCQ schema."""
    expected_count = max(1, int(expected_count))
    numerical_target_ratio = max(0.0, min(1.0, float(numerical_target_ratio)))
    normalized: list[dict[str, Any]] = []
    seen_prompts: set[str] = set()
    if isinstance(raw_questions, list):
        for raw in raw_questions:
            if not isinstance(raw, dict):
                continue

            prompt = str(raw.get("question") or raw.get("prompt") or "").strip()
            if not prompt:
                continue
            prompt_key = _normalize_for_compare(prompt)
            if not prompt_key or prompt_key in seen_prompts:
                continue

            raw_options = raw.get("options", [])
            options: list[str] = []
            if isinstance(raw_options, list):
                for opt in raw_options:
                    value = str(opt).strip()
                    if value:
                        options.append(value)

            options = options[:MCQ_OPTION_COUNT]
            while len(options) < MCQ_OPTION_COUNT:
                options.append(f"Option {chr(65 + len(options))}")

            if _is_low_quality_question(prompt, options):
                continue

            correct_index = _safe_int(raw.get("correct_index"), default=0)
            if correct_index < 0 or correct_index >= len(options):
                correct_index = 0

            concept = str(raw.get("concept") or raw.get("tag") or subtopic or "General").strip()
            if not concept:
                concept = subtopic or "General"

            normalized.append(
                {
                    "question_id": "placeholder",
                    "question": prompt,
                    "options": options,
                    "correct_index": correct_index,
                    "concept": concept,
                }
            )
            seen_prompts.add(prompt_key)
            if len(normalized) == expected_count:
                break

    if len(normalized) < expected_count:
        fallback = build_fallback_questions(
            subtopic,
            expected_count=expected_count,
            numerical_target_ratio=numerical_target_ratio,
        )
        used_prompts = {q.get("question", "").strip().lower() for q in normalized}
        for candidate in fallback:
            prompt = str(candidate.get("question", "")).strip().lower()
            if prompt in used_prompts:
                continue
            normalized.append(candidate)
            used_prompts.add(prompt)
            if len(normalized) == expected_count:
                break

    normalized = _ensure_numerical_ratio(
        normalized[:expected_count],
        subtopic=subtopic,
        expected_count=expected_count,
        numerical_target_ratio=numerical_target_ratio,
    )
    for idx, q in enumerate(normalized, start=1):
        q["question_id"] = f"q{idx}"

    return normalized


def compute_numerical_ratio(questions: Any) -> float:
    if not isinstance(questions, list) or not questions:
        return 0.0
    numerical_count = sum(1 for q in questions if is_numerical_question(q))
    return numerical_count / len(questions)


def is_numerical_question(question: Any) -> bool:
    if not isinstance(question, dict):
        return False
    prompt = str(question.get("question", "")).lower()
    options = question.get("options", [])
    option_text = " ".join(str(o).lower() for o in options) if isinstance(options, list) else ""
    blob = f"{prompt} {option_text}"
    if re.search(r"\d", blob):
        return True
    if re.search(r"\d+\s*[\+\-\*\/=]\s*\d+", blob):
        return True
    return any(cue in blob for cue in _NUMERICAL_CUES)


def validate_mcq_submission(quiz_questions: Any, answers: Any) -> list[int]:
    """Validate submitted answer indexes against the quiz shape."""
    if not isinstance(quiz_questions, list) or len(quiz_questions) == 0:
        raise ValueError("Quiz is not available for this session yet.")
    if not isinstance(answers, list):
        raise ValueError("answers must be an array of integers.")
    if len(answers) != len(quiz_questions):
        raise ValueError(
            f"answers length mismatch: expected {len(quiz_questions)}, got {len(answers)}."
        )

    validated: list[int] = []
    for idx, answer in enumerate(answers):
        if isinstance(answer, bool) or not isinstance(answer, int):
            raise ValueError(f"answers[{idx}] must be an integer option index.")

        options = quiz_questions[idx].get("options", []) if isinstance(quiz_questions[idx], dict) else []
        option_count = len(options) if isinstance(options, list) else 0
        if option_count <= 0:
            raise ValueError(f"quiz question {idx + 1} has invalid options.")
        if answer < 0 or answer >= option_count:
            raise ValueError(
                f"answers[{idx}] out of range. Expected 0..{option_count - 1}, got {answer}."
            )
        validated.append(answer)

    return validated


def determine_next_action(
    *,
    passed: bool,
    current_node: str,
    subtopics: list[str],
    remediation_count: int,
    max_remediation: int,
    history: list[dict[str, Any]] | None = None,
    mastery: dict[str, bool] | None = None,
) -> str:
    """Return next action label aligned with router behavior."""
    history = history or []
    mastery = mastery or {}

    # For graph-like traversal, completion means all curriculum subtopics are mastered.
    # If mastery map is unavailable, we fall back to legacy index-based behavior.
    if mastery:
        remaining = [st for st in subtopics if not mastery.get(st, False) and st != current_node]
        if passed:
            return "next_topic" if remaining else "completed"
        if remediation_count < max_remediation:
            return "remediation"
        return "next_topic" if remaining else "completed"

    if passed:
        idx = _current_subtopic_index(current_node, subtopics, history)
        if idx + 1 < len(subtopics):
            return "next_topic"
        return "completed"

    if remediation_count < max_remediation:
        return "remediation"

    idx = _current_subtopic_index(current_node, subtopics, history)
    if idx + 1 < len(subtopics):
        return "next_topic"
    return "completed"


def grade_mcq(
    *,
    subtopic: str,
    quiz_questions: Any,
    user_answers: Any,
    subtopics: list[str],
    remediation_count: int,
    max_remediation: int,
    mastery_threshold: float,
    history: list[dict[str, Any]] | None = None,
    mastery: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Grade MCQ answers deterministically and return a full evaluation payload."""
    if not isinstance(quiz_questions, list) or len(quiz_questions) == 0:
        raise ValueError("No quiz questions available for deterministic grading.")

    answers = validate_mcq_submission(quiz_questions, user_answers)

    results: list[dict[str, Any]] = []
    weak_areas: list[str] = []
    correct_count = 0

    for idx, q in enumerate(quiz_questions):
        if not isinstance(q, dict):
            raise ValueError(f"Malformed quiz question at index {idx}.")

        question = str(q.get("question") or "").strip()
        question_id = str(q.get("question_id") or f"q{idx + 1}").strip()
        options = q.get("options", [])
        if not isinstance(options, list) or len(options) == 0:
            raise ValueError(f"Malformed options for question {idx + 1}.")

        correct_index = _safe_int(q.get("correct_index"), default=-1)
        if correct_index < 0 or correct_index >= len(options):
            raise ValueError(f"Invalid correct_index for question {idx + 1}.")

        user_index = answers[idx]
        is_correct = user_index == correct_index
        if is_correct:
            correct_count += 1
        else:
            concept = str(q.get("concept") or subtopic).strip()
            if concept and concept not in weak_areas:
                weak_areas.append(concept)

        results.append(
            {
                "question_id": question_id,
                "question": question,
                "options": [str(o) for o in options],
                "correct_index": correct_index,
                "user_index": user_index,
                "is_correct": is_correct,
            }
        )

    score = correct_count / len(quiz_questions)
    passed = score >= mastery_threshold
    next_action = determine_next_action(
        passed=passed,
        current_node=subtopic,
        subtopics=subtopics,
        remediation_count=remediation_count,
        max_remediation=max_remediation,
        history=history,
        mastery=mastery,
    )
    feedback = build_feedback(subtopic=subtopic, score=score, weak_areas=weak_areas)

    return {
        "score": score,
        "feedback": feedback,
        "weak_areas": weak_areas,
        "passed": passed,
        "next_action": next_action,
        "question_results": results,
        "total_questions": len(quiz_questions),
        "correct_count": correct_count,
    }


def build_feedback(*, subtopic: str, score: float, weak_areas: list[str]) -> str:
    """Build deterministic user feedback from score bands and weak areas."""
    topic = subtopic or "this topic"
    areas = ", ".join(weak_areas[:3]) if weak_areas else "core concepts from this lesson"
    next_step = f"Next steps: review {areas}, then retry a similar quiz."
    if score >= 0.95:
        return (
            f"Excellent work on {topic}. You answered every question correctly and demonstrated strong mastery. "
            f"{next_step}"
        )
    if score >= 0.8:
        return (
            f"Great job on {topic}. Your understanding is strong and only small gaps remain. "
            f"{next_step}"
        )
    if score >= 0.5:
        return (
            f"You have partial understanding of {topic}. Focus on targeted revision to improve consistency. "
            f"{next_step}"
        )
    return (
        f"You are still building your foundation in {topic}. Start with the basics and build up step by step. "
        f"{next_step}"
    )


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _current_subtopic_index(current_node: str, subtopics: list[str], history: list[dict[str, Any]]) -> int:
    if current_node in subtopics:
        return subtopics.index(current_node)

    parent = _find_bridge_parent(history, current_node)
    if parent and parent in subtopics:
        return subtopics.index(parent)
    return len(subtopics) - 1 if subtopics else 0


def _find_bridge_parent(history: list[dict[str, Any]], bridge_topic: str) -> str | None:
    for entry in reversed(history):
        if entry.get("type") == "bridge" and entry.get("bridge_topic") == bridge_topic:
            return entry.get("parent_subtopic")
    return None


def _ensure_numerical_ratio(
    questions: list[dict[str, Any]],
    *,
    subtopic: str,
    expected_count: int,
    numerical_target_ratio: float,
) -> list[dict[str, Any]]:
    if numerical_target_ratio <= 0:
        return questions
    required = int(round(expected_count * numerical_target_ratio))
    if required <= 0:
        return questions

    numerical_indexes = [idx for idx, q in enumerate(questions) if is_numerical_question(q)]
    if len(numerical_indexes) >= required:
        return questions

    fallbacks = build_fallback_questions(
        subtopic,
        expected_count=expected_count,
        numerical_target_ratio=numerical_target_ratio,
    )
    fallback_numerical = [q for q in fallbacks if is_numerical_question(q)]
    if not fallback_numerical:
        return questions

    out = list(questions)
    fb_idx = 0
    for idx, q in enumerate(out):
        if len(numerical_indexes) >= required:
            break
        if is_numerical_question(q):
            continue
        replacement = dict(fallback_numerical[fb_idx % len(fallback_numerical)])
        out[idx] = replacement
        numerical_indexes.append(idx)
        fb_idx += 1
    return out


def _is_low_quality_question(prompt: str, options: list[str]) -> bool:
    normalized_prompt = str(prompt or "").strip()
    if len(re.findall(r"\w+", normalized_prompt)) < 5:
        return True
    if _looks_like_gibberish(normalized_prompt):
        return True
    if re.search(r"[\{\[\<]\s*(todo|tbd|insert)", normalized_prompt, flags=re.IGNORECASE):
        return True

    lower_prompt = normalized_prompt.lower()
    if lower_prompt.endswith(("from one city to another", "from one point to another")):
        return True

    placeholder_like = 0
    empty_like = 0
    seen_options: set[str] = set()
    substantive_options = 0
    for raw_opt in options:
        opt = str(raw_opt or "").strip()
        if not opt:
            empty_like += 1
            continue
        opt_key = _normalize_for_compare(opt)
        if not opt_key:
            empty_like += 1
            continue
        if opt_key in seen_options:
            return True
        seen_options.add(opt_key)

        lower_opt = opt.lower()
        if any(phrase in lower_opt for phrase in _FORBIDDEN_OPTION_PHRASES):
            return True
        if _looks_like_gibberish(opt):
            return True
        if re.fullmatch(r"option\s+[a-d]", opt.lower()):
            placeholder_like += 1
        token_count = len(re.findall(r"\w+", opt))
        has_digits = bool(re.search(r"\d", opt))
        if token_count < 2 and not has_digits:
            placeholder_like += 1
        if token_count >= 3 or has_digits:
            substantive_options += 1

    if empty_like > 0:
        return True
    if placeholder_like >= 2:
        return True
    if substantive_options < 2:
        return True
    return False


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text or "").lower())).strip()


def _looks_like_gibberish(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return True
    if any(marker in normalized for marker in _GIBBERISH_MARKERS):
        return True
    if re.search(r"(.)\1{4,}", normalized):
        return True
    tokens = re.findall(r"[a-z0-9]+", normalized)
    if not tokens:
        return True
    if len(tokens) >= 6:
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        most_common = max(counts.values())
        if most_common / len(tokens) >= 0.5:
            return True
    return False
