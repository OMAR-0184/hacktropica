from __future__ import annotations

import re


def check_quiz_quality(questions: list[dict]) -> list[str]:
    """
    Detect quality issues in generated quiz questions.

    Returns a list of issue descriptions (empty if quality is acceptable).
    """
    issues: list[str] = []

    # 1. Correct answer always at the same index.
    correct_indexes = [
        q.get("correct_index", 0)
        for q in questions
        if isinstance(q, dict) and "correct_index" in q
    ]
    if correct_indexes and len(set(correct_indexes)) == 1 and len(correct_indexes) > 2:
        issues.append(
            f"All correct answers are at index {correct_indexes[0]}. "
            f"Vary the position of correct answers."
        )

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue
        stem = str(q.get("question", "")).strip()
        options = q.get("options", [])
        if not isinstance(options, list):
            continue

        # 2. Question stem too long (>60 words).
        word_count = len(re.findall(r"\w+", stem))
        if word_count > 60:
            issues.append(
                f"Question {i+1} is too verbose ({word_count} words). "
                f"Keep it to 1-2 sentences."
            )

        # 3. Double negatives.
        lower_stem = stem.lower()
        if "not incorrect" in lower_stem or "not untrue" in lower_stem:
            issues.append(
                f"Question {i+1} uses a double negative. Rephrase positively."
            )

        # 4. Options are near-duplicates.
        opt_normalized = [
            re.sub(r"\s+", " ", str(o).strip().lower()) for o in options
        ]
        for a_idx in range(len(opt_normalized)):
            for b_idx in range(a_idx + 1, len(opt_normalized)):
                if opt_normalized[a_idx] == opt_normalized[b_idx]:
                    issues.append(
                        f"Question {i+1} has duplicate options "
                        f"({a_idx+1} and {b_idx+1})."
                    )

        # 5. Correct answer is always the longest option.
        correct_idx = q.get("correct_index", 0)
        if isinstance(correct_idx, int) and 0 <= correct_idx < len(options):
            opt_lengths = [len(str(o)) for o in options]
            if opt_lengths[correct_idx] == max(opt_lengths):
                # Only flag if significantly longer (>50% longer than average of others).
                others = [
                    l for j, l in enumerate(opt_lengths) if j != correct_idx
                ]
                if others:
                    avg_other = sum(others) / len(others)
                    if avg_other > 0 and opt_lengths[correct_idx] / avg_other > 1.5:
                        issues.append(
                            f"Question {i+1}: correct answer is significantly "
                            f"longer than other options. Balance option lengths."
                        )

    # Deduplicate issues.
    return list(dict.fromkeys(issues))
