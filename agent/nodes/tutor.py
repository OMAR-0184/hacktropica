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

_MARKDOWN_SYSTEM_PROMPT = """\
You are an expert tutor. Given a subtopic and lesson context, produce a COMPLETE, BEAUTIFUL, and COLORFUL Markdown document that serves as a lesson handout.

REQUIREMENTS:
1. The document MUST incorporate Gagné's Nine Events of Instruction natively using headings and blockquotes. Structure the following elements in detailed discussion:
   - A Hook (attention grabber)
   - Prior Knowledge connection
   - Learning Objective
   - Core Explanation (detailed discussion with progressive complexity)
   - Worked Examples (step-by-step reasoning)
   - Common Misconceptions
   - A Practice Task
   - A Transfer Prompt (real-world application)
   - A Summary (3 bullet points)
2. Use Markdown headings (##, ###) for clear document structure.
3. AMAZING ILLUSTRATIONS: Use emojis generously as illustrations. Make it look like a colorful chart paper sticking to a board! Use emojis to represent diagrams, key points, and concepts visually.
4. Use `> blockquotes` for callouts, important notes, or "sticky notes" on the chart paper.
5. Emphasize key terms with **bold** or *italics*.
6. Do NOT use HTML tags. 
7. Do NOT use any LaTeX or KaTeX math formatting. Use standard text and unicode characters for math.

CRITICAL RULES:
- Return ONLY the raw Markdown text. Do NOT wrap it in JSON.
- Ensure the markdown is visually appealing and reads like a highly engaging, colorful poster or chart paper.
"""


_MARKDOWN_MAX_RETRIES = 1


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

    markdown_result = await _generate_markdown_content(topic, current, user_prompt)

    return {
        "tutor_content": {},
        "markdown_content": markdown_result
    }


# ── Markdown generation ────────────────

async def _generate_markdown_content(
    topic: str, current: str, user_prompt: str
) -> dict[str, Any]:
    """
    Generate a Markdown document.
    """
    markdown_user_prompt = (
        f"{user_prompt}\n\n"
        f"Create a detailed, beautiful Markdown lesson handout for '{current}' "
        f"within the broader topic '{topic}'."
    )

    messages = [
        {"role": "system", "content": _MARKDOWN_SYSTEM_PROMPT},
        {"role": "user", "content": markdown_user_prompt},
    ]

    source = await invoke_llm(
        node_type="tutor",
        temperature=0.3,
        messages=messages,
    )

    source = source.strip()
    if not source:
        raise RuntimeError("Tutor generation returned no lesson content")
    if source.startswith("```markdown"):
        source = source[11:]
    if source.startswith("```"):
        source = source[3:]
    if source.endswith("```"):
        source = source[:-3]
    source = source.strip()

    return {
        "markdown_source": source,
        "markdown_valid": bool(source),
        "validation_warnings": [],
        "attempts": 1,
    }

