"""
Deterministic next-node recommendation engine.

Scores each candidate node using a weighted combination of historical
performance, recency, traversal order, depth, and pedagogical sequencing.
The result is fully deterministic — no randomness or LLM calls.
"""

from __future__ import annotations

from typing import Any

from api.services.graph_helpers import (
    normalize_journey_mode,
    safe_int,
)


def recommend_next_node(
    values: dict, options: list[str], traversal_mode: str
) -> dict[str, Any]:
    """Return the best next node with explanation and scoring factors."""
    if not options:
        return {"node": None, "reason": None, "factors": {}}

    scores = values.get("scores", {})
    graph_nodes = values.get("graph_nodes", {})
    mastery = values.get("mastery", {})
    navigation_stack = values.get("navigation_stack", [])
    journey_mode = normalize_journey_mode(values.get("journey_mode"))
    for d in (scores, graph_nodes, mastery):
        if not isinstance(d, dict):
            d = {}  # noqa: PLW2901
    if not isinstance(navigation_stack, list):
        navigation_stack = []

    node_catalog = values.get("node_catalog", {})
    if not isinstance(node_catalog, dict):
        node_catalog = {}

    recent = [str(n) for n in navigation_stack[-3:]]
    current_node = str(values.get("current_node", "") or "")
    current_meta = node_catalog.get(current_node, {})
    current_depth = (
        safe_int(current_meta.get("depth", 0), 0)
        if isinstance(current_meta, dict)
        else 0
    )
    current_kind = (
        str(current_meta.get("node_kind", "concept") or "concept").lower()
        if isinstance(current_meta, dict)
        else "concept"
    )

    # Check whether any pending concept-type node exists
    has_pending_concept = _has_pending_concept(options, node_catalog, mastery)

    scored: list[tuple[str, float, dict[str, Any]]] = []
    for idx, node in enumerate(options):
        total, factors = _score_node(
            node=node,
            idx=idx,
            scores=scores,
            graph_nodes=graph_nodes,
            node_catalog=node_catalog,
            recent=recent,
            traversal_mode=traversal_mode,
            journey_mode=journey_mode,
            current_depth=current_depth,
            current_kind=current_kind,
            has_pending_concept=has_pending_concept,
        )
        scored.append((node, total, factors))

    best_node, _, factors = max(scored, key=lambda x: x[1])
    reason = (
        f"Recommended by deterministic priority ({traversal_mode.upper()} mode): "
        "weaker/unseen areas first, foundational concept sequencing, "
        "recently visited nodes deprioritized, then traversal tie-break."
    )
    return {"node": best_node, "reason": reason, "factors": factors}


# ── Scoring internals ─────────────────────────────────────────


def _has_pending_concept(
    options: list[str],
    node_catalog: dict,
    mastery: dict,
) -> bool:
    """True if at least one un-mastered concept-type node is in *options*."""
    for node in options:
        meta = node_catalog.get(node, {})
        kind = (
            str(meta.get("node_kind", "concept") or "concept").lower()
            if isinstance(meta, dict)
            else "concept"
        )
        if kind == "concept" and not mastery.get(node, False):
            return True
    return False


def _score_node(
    *,
    node: str,
    idx: int,
    scores: dict,
    graph_nodes: dict,
    node_catalog: dict,
    recent: list[str],
    traversal_mode: str,
    journey_mode: str,
    current_depth: int,
    current_kind: str,
    has_pending_concept: bool,
) -> tuple[float, dict[str, Any]]:
    """Compute a composite priority score for a single candidate node."""
    hist_score = scores.get(node)
    has_history = hist_score is not None

    # Historical priority — weaker nodes score higher
    if has_history:
        try:
            normalized = float(hist_score)
        except (TypeError, ValueError):
            normalized = 0.5
        historical_priority = (1.0 - max(0.0, min(1.0, normalized))) * 100.0
        unseen_bonus = 0.0
    else:
        normalized = None
        historical_priority = 35.0
        unseen_bonus = 15.0

    recency_penalty = -20.0 if node in recent else 0.0
    tiebreak = (-idx / 1000.0) if traversal_mode == "bfs" else (idx / 1000.0)

    # Attempt penalty — avoid repeatedly drilling the same node
    attempts = 0
    node_meta_gn = graph_nodes.get(node)
    if isinstance(node_meta_gn, dict):
        attempts = int(node_meta_gn.get("attempts", 0))
    attempt_penalty = -min(float(attempts), 5.0)

    # Depth & kind factors
    node_meta = node_catalog.get(node, {})
    node_depth = (
        safe_int(node_meta.get("depth", 0), 0) if isinstance(node_meta, dict) else 0
    )
    node_kind = (
        str(node_meta.get("node_kind", "concept") or "concept").lower()
        if isinstance(node_meta, dict)
        else "concept"
    )
    depth_delta = node_depth - current_depth
    depth_factor = (
        float(depth_delta) if traversal_mode == "dfs" else float(-depth_delta)
    )

    # Pedagogical sequencing — prefer concepts before advanced topics
    sequencing_bonus = 0.0
    if journey_mode == "learn":
        if node_kind == "concept":
            sequencing_bonus += 10.0
        elif node_kind == "advanced":
            sequencing_bonus -= 10.0
        if current_kind == "intro" and node_kind == "advanced":
            sequencing_bonus -= 8.0
        if has_pending_concept and node_kind == "advanced":
            sequencing_bonus -= 12.0

    total = (
        historical_priority
        + unseen_bonus
        + recency_penalty
        + tiebreak
        + attempt_penalty
        + depth_factor
        + sequencing_bonus
    )
    factors = {
        "historical_priority": round(historical_priority, 3),
        "unseen_bonus": round(unseen_bonus, 3),
        "recency_penalty": round(recency_penalty, 3),
        "attempt_penalty": round(attempt_penalty, 3),
        "depth_factor": round(depth_factor, 3),
        "sequencing_bonus": round(sequencing_bonus, 3),
        "node_kind": node_kind,
        "journey_mode": journey_mode,
        "traversal_tiebreak": round(tiebreak, 6),
        "historical_score": normalized,
    }
    return total, factors
