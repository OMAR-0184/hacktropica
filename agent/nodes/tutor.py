"""
tutor_node — Generates structured lesson content + LaTeX document for the
current subtopic.

Outputs:
  1. **Pedagogical JSON** following Gagné's Nine Events of Instruction,
     integrated with Bloom's Taxonomy depth cues.
  2. **LaTeX source** — a colorful, self-contained document with diagrams
     (TikZ), styled boxes (tcolorbox), and equations (amsmath).  The raw
     `.tex` is sent to the client; rendering happens Flutter-side.
  3. A structural validation guardrail checks the LaTeX and feeds errors
     back to the LLM for self-correction (max 2 retries) without ever
     invoking a compiler.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from agent.nodes._llm_call import invoke_llm
from agent.guardrails.latex_syntax import validate_latex, ValidationResult
from agent.state import CognimapState

logger = logging.getLogger(__name__)

# ── System prompts ────────────────────────────────────────────

_LATEX_SYSTEM_PROMPT = """\
You are an expert tutor and LaTeX document author. Given a subtopic and lesson context,
produce a COMPLETE, COMPILABLE LaTeX document that serves as a beautiful, colorful lesson handout.

REQUIREMENTS:
1. Use \\documentclass[12pt]{article}
2. Use ONLY these packages: amsmath, amssymb, xcolor, tikz, tcolorbox, geometry,
   enumitem, hyperref, fontenc, inputenc, booktabs, tabularx
3. Define 4-5 custom colors using \\definecolor with attractive, modern tones
   (e.g. deep blues, teals, warm oranges, purples — NOT plain red/green/blue).
4. The document MUST incorporate Gagné's Nine Events of Instruction natively. Use `tcolorbox` or `\\section` to structure the following elements in detailed discussion:
   - A Hook (attention grabber)
   - Prior Knowledge connection
   - Learning Objective
   - Core Explanation (detailed discussion with progressive complexity)
   - Worked Examples (step-by-step reasoning)
   - Common Misconceptions
   - A Practice Task
   - A Transfer Prompt (real-world application)
   - A Summary (3 bullet points)
5. Include at least ONE amazing, highly descriptive TikZ diagram that illustrates the core concept in vivid detail.
6. Use \\section, \\subsection for clear document structure.
7. Use proper mathematical typesetting for ALL equations/formulas.
8. The document must be SELF-CONTAINED — do not reference external files.
9. Use \\color{} and \\textcolor{} generously to make headings and key terms visually amazing.

CRITICAL RULES:
- Return ONLY the raw LaTeX source code. Do NOT wrap it in JSON. Do NOT wrap it in markdown backticks (e.g. ```latex). Just return the raw LaTeX string starting with \\documentclass.
- Every \\begin{X} MUST have a matching \\end{X}.
- Every opening { MUST have a closing }.
- Every opening $ MUST have a closing $.
- Do NOT leave any environment empty.
- Do NOT use packages not listed above.
"""

_LATEX_MAX_RETRIES = 2


# ── Public entry point ────────────────────────────────────────


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
        user_prompt += (
            f"\n\nHistorical Learner Weaknesses to explicitly "
            f"address/simplify in this lesson:\n{learner_profile}"
        )

    latex_result = await _generate_latex_content(topic, current, user_prompt)

    return {
        "tutor_content": {},
        "latex_content": latex_result,
    }


# ── LaTeX generation with validation guardrail ────────────────


async def _generate_latex_content(
    topic: str, current: str, user_prompt: str
) -> dict[str, Any]:
    """
    Generate a LaTeX document and validate it structurally.

    If validation fails, feed the errors back to the LLM and retry
    (up to ``_LATEX_MAX_RETRIES`` times).  On final failure, return
    empty LaTeX with ``latex_valid=False``.
    """
    latex_user_prompt = (
        f"{user_prompt}\n\n"
        f"Create a beautiful, colorful LaTeX lesson handout for '{current}' "
        f"within the broader topic '{topic}'."
    )

    messages = [
        {"role": "system", "content": _LATEX_SYSTEM_PROMPT},
        {"role": "user", "content": latex_user_prompt},
    ]

    last_validation: ValidationResult | None = None

    for attempt in range(1, _LATEX_MAX_RETRIES + 2):  # 1-indexed, up to max+1
        latex_source = await invoke_llm(
            node_type="tutor",
            temperature=0.15,
            messages=messages,
        )

        latex_source = latex_source.strip()
        # Clean up markdown fences just in case
        if latex_source.startswith("```latex"):
            latex_source = latex_source[8:]
        if latex_source.startswith("```"):
            latex_source = latex_source[3:]
        if latex_source.endswith("```"):
            latex_source = latex_source[:-3]
        latex_source = latex_source.strip()
        if not latex_source:
            logger.warning(
                "[tutor/latex] Attempt %d: LLM returned empty LaTeX source.",
                attempt,
            )
            if attempt <= _LATEX_MAX_RETRIES:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The LaTeX source you returned was empty. "
                            "Please generate a complete LaTeX document."
                        ),
                    }
                )
                continue
            break

        # ── Structural validation guardrail ───────────────────
        validation = validate_latex(latex_source)
        last_validation = validation

        if validation.valid:
            logger.info(
                "[tutor/latex] LaTeX validated successfully on attempt %d "
                "(warnings: %d).",
                attempt,
                len(validation.warnings),
            )
            return {
                "latex_source": latex_source,
                "latex_valid": True,
                "validation_warnings": validation.warnings,
                "attempts": attempt,
            }

        # Validation failed — feed errors back for retry.
        logger.warning(
            "[tutor/latex] Attempt %d: validation failed with %d error(s): %s",
            attempt,
            len(validation.errors),
            "; ".join(validation.errors),
        )
        if attempt <= _LATEX_MAX_RETRIES:
            messages.append(
                {"role": "assistant", "content": latex_source}
            )
            messages.append(
                {"role": "user", "content": validation.feedback_for_llm}
            )

    # All retries exhausted.
    logger.error(
        "[tutor/latex] All %d LaTeX attempts failed. Returning invalid.",
        _LATEX_MAX_RETRIES + 1,
    )
    return {
        "latex_source": latex_source if "latex_source" in dir() else "",
        "latex_valid": False,
        "validation_errors": (
            last_validation.errors if last_validation else ["Generation failed."]
        ),
        "validation_warnings": (
            last_validation.warnings if last_validation else []
        ),
        "attempts": _LATEX_MAX_RETRIES + 1,
    }


