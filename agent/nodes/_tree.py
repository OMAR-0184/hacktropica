"""
Shared tree/hierarchy helpers for adaptive curriculum traversal.
"""

from __future__ import annotations

import re
from typing import Any

from agent.nodes._llm_call import invoke_llm_json

_MATH_TERMS = {
    "math",
    "mathematics",
    "algebra",
    "geometry",
    "trigonometry",
    "calculus",
    "equation",
    "derivative",
    "integral",
    "matrix",
    "vector",
    "probability",
    "statistics",
    "kinematics",
    "velocity",
    "acceleration",
    "force",
    "momentum",
    "numerical",
}


def infer_math_heavy(text: str) -> bool:
    lower = str(text or "").lower()
    if re.search(r"\b\d+\b", lower):
        return True
    return any(term in lower for term in _MATH_TERMS)


def build_node_meta(
    *,
    node_id: str,
    parent_node_id: str | None,
    depth: int,
    node_kind: str,
    is_math_heavy: bool,
    parent_path: list[str] | None = None,
    is_expanded: bool = False,
) -> dict[str, Any]:
    path = list(parent_path or [])
    path.append(node_id)
    return {
        "node_id": node_id,
        "parent_node_id": parent_node_id,
        "depth": int(depth),
        "node_kind": node_kind if node_kind in {"intro", "concept", "advanced", "remediation"} else "concept",
        "path_from_root": path,
        "is_math_heavy": bool(is_math_heavy),
        "is_expanded": bool(is_expanded),
    }


def determine_quiz_profile(node_meta: dict[str, Any] | None, node_id: str) -> tuple[int, float]:
    meta = node_meta or {}
    node_kind = str(meta.get("node_kind", "") or "").lower()
    math_heavy = bool(meta.get("is_math_heavy", False))
    normalized_id = str(node_id or "").strip().lower()

    if node_kind == "intro" or normalized_id.startswith("intro to "):
        return 5, 0.0
    if math_heavy:
        return 10, 0.6
    return 7, 0.0


def uniquify_titles(raw_titles: list[str], existing: set[str]) -> list[str]:
    out: list[str] = []
    used = set(existing)
    for raw in raw_titles:
        title = str(raw or "").strip()
        if not title:
            continue
        lowered = title.lower()
        if lowered in used:
            continue
        out.append(title)
        used.add(lowered)
    return out


async def generate_child_blueprint(
    *,
    topic: str,
    parent_node: str,
    parent_depth: int,
    weak_areas: list[str],
    min_children: int,
    max_children: int,
    course_mode: str,
    existing_titles: set[str],
) -> list[dict[str, Any]]:
    min_children = max(1, int(min_children))
    max_children = max(min_children, int(max_children))

    system_prompt = (
        "You are an elite curriculum architect.\n"
        f"Generate {min_children}-{max_children} child subtopics that are the best immediate next learning steps.\n"
        "The child topics must be specific, progressively deeper, and non-redundant.\n"
        "Return ONLY JSON with this shape:\n"
        '{"children":[{"title":"...", "is_math_heavy": true, "node_kind": "concept"}]}'
    )
    user_prompt = (
        f"Broader topic: {topic}\n"
        f"Current parent node: {parent_node}\n"
        f"Current depth: {parent_depth}\n"
        f"Course mode: {course_mode}\n"
        f"Weak areas (if any): {weak_areas}\n"
        "Rules:\n"
        "- Use concise titles suitable for node names.\n"
        "- At least one child should be practical/application-oriented.\n"
        '- node_kind must be either "concept" or "advanced".\n'
        "- Mark is_math_heavy true when the child needs calculations/equations."
    )

    try:
        data = await invoke_llm_json(
            node_type="root",
            temperature=0.25,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            required_keys=["children"],
            defaults={"children": []},
        )
    except Exception:
        # Never fail graph progression due to child generation instability.
        data = {"children": []}

    children: list[dict[str, Any]] = []
    raw_children = data.get("children", [])
    if isinstance(raw_children, list):
        for item in raw_children:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            node_kind = str(item.get("node_kind", "concept")).strip().lower()
            if node_kind not in {"concept", "advanced"}:
                node_kind = "concept"
            math_heavy = bool(item.get("is_math_heavy", infer_math_heavy(title)))
            children.append(
                {
                    "title": title,
                    "is_math_heavy": math_heavy,
                    "node_kind": node_kind,
                }
            )

    unique_titles = uniquify_titles([c["title"] for c in children], existing_titles)
    normalized: list[dict[str, Any]] = []
    title_to_child = {c["title"]: c for c in children}
    for title in unique_titles:
        child = title_to_child.get(title, {})
        normalized.append(
            {
                "title": title,
                "is_math_heavy": bool(child.get("is_math_heavy", infer_math_heavy(title))),
                "node_kind": str(child.get("node_kind", "concept")),
            }
        )

    if len(normalized) < min_children:
        fallback = [
            f"Core Concepts of {parent_node}",
            f"Applications of {parent_node}",
            f"Advanced {parent_node}",
            f"Problem Solving in {parent_node}",
        ]
        for title in fallback:
            candidate = str(title).strip()
            if candidate.lower() in existing_titles:
                continue
            if any(c["title"].lower() == candidate.lower() for c in normalized):
                continue
            normalized.append(
                {
                    "title": candidate,
                    "is_math_heavy": infer_math_heavy(candidate) or infer_math_heavy(topic),
                    "node_kind": "advanced" if "advanced" in candidate.lower() else "concept",
                }
            )
            if len(normalized) >= min_children:
                break

    return normalized[:max_children]
