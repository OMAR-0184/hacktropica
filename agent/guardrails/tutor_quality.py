from __future__ import annotations

import re
from typing import Any


def check_tutor_quality(content: dict[str, Any], course_mode: str) -> bool:
    """Check whether the generated text content is below the quality bar.
    
    Returns True if the content needs to be re-generated.
    """
    explanation = str(
        content.get("core_explanation", content.get("explanation", ""))
    ).strip()
    examples = content.get("worked_examples", content.get("examples", []))
    if not isinstance(examples, list):
        examples = []

    word_count = len(re.findall(r"\w+", explanation))
    lower = explanation.lower()
    bad_phrase_hits = sum(
        lower.count(p) for p in ("tiny", "special path", "tiny atom", "tiny ball")
    )

    if course_mode == "detailed":
        if word_count < 90:
            return True
        if bad_phrase_hits >= 2:
            return True
        if any("imagine" in str(ex).lower() for ex in examples):
            return True
        # Require at least 2 worked examples in detailed mode.
        if len(examples) < 2:
            return True
    else:
        if word_count < 45:
            return True
        if bad_phrase_hits >= 3:
            return True

    return False
