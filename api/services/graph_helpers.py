"""
Pure helpers for reading and normalising LangGraph checkpoint state.

Every function here is side-effect-free — it only transforms dicts/lists that
were already loaded from a snapshot.  This makes the helpers easy to unit-test
and reusable across services without circular imports.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from api.schemas.learning import (
    ContinueRequest,
    NodeHierarchyMeta,
)


# ── Type-safe coercion ────────────────────────────────────────


def safe_int(value: Any, default: int = 0) -> int:
    """Coerce *value* to int, falling back to *default* on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float | None = 0.0) -> float | None:
    """Coerce *value* to float, falling back to *default* on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Snapshot introspection ────────────────────────────────────


def snapshot_next_nodes(snapshot) -> list[str]:
    """Return the list of graph nodes waiting for input in a checkpoint."""
    nodes = getattr(snapshot, "next", ()) or ()
    if isinstance(nodes, (list, tuple)):
        return [str(n) for n in nodes]
    return []


# ── Normalisation helpers ─────────────────────────────────────


def normalize_journey_mode(value: str | None) -> str:
    mode = str(value or "learn").strip().lower()
    return mode if mode in {"learn", "review"} else "learn"


def normalize_traversal_mode(value: str | None) -> str:
    mode = str(value or "dfs").strip().lower()
    return mode if mode in {"bfs", "dfs"} else "dfs"


def normalize_node_list(value: Any) -> list[str]:
    """Flatten *value* into a list of non-empty stripped strings."""
    if not isinstance(value, list):
        return []
    return [s for node in value if (s := str(node).strip())]


def normalize_children_map(value: Any) -> dict[str, list[str]]:
    """Ensure every key maps to a clean list of child-node IDs."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for parent, children in value.items():
        parent_id = str(parent).strip()
        if not parent_id:
            continue
        if isinstance(children, list):
            out[parent_id] = [s for child in children if (s := str(child).strip())]
        else:
            out[parent_id] = []
    return out


# ── Node metadata extraction ─────────────────────────────────


def get_node_meta(values: dict, node_id: str | None) -> dict[str, Any]:
    """Pull hierarchy metadata for *node_id* from the node_catalog."""
    if not node_id:
        return {}
    catalog = values.get("node_catalog", {})
    if not isinstance(catalog, dict):
        return {}
    raw = catalog.get(node_id, {})
    if not isinstance(raw, dict):
        return {}
    path = raw.get("path_from_root", [])
    if not isinstance(path, list):
        path = []
    return {
        "parent_node_id": raw.get("parent_node_id"),
        "depth": raw.get("depth"),
        "node_kind": raw.get("node_kind"),
        "path_from_root": path,
        "is_math_heavy": raw.get("is_math_heavy"),
        "is_expanded": raw.get("is_expanded"),
    }


def build_node_catalog_list(values: dict) -> list[NodeHierarchyMeta]:
    """Build a sorted list of typed node-hierarchy entries from graph state."""
    catalog = values.get("node_catalog", {})
    if not isinstance(catalog, dict):
        return []
    graph_nodes = values.get("graph_nodes", {})
    if not isinstance(graph_nodes, dict):
        graph_nodes = {}
    scores = values.get("scores", {})
    if not isinstance(scores, dict):
        scores = {}

    out: list[NodeHierarchyMeta] = []
    for node_id, raw in catalog.items():
        if not isinstance(raw, dict):
            continue
        path_from_root = raw.get("path_from_root", [])
        if not isinstance(path_from_root, list):
            path_from_root = []
        graph_meta = graph_nodes.get(node_id, {})
        if not isinstance(graph_meta, dict):
            graph_meta = {}
        out.append(
            NodeHierarchyMeta(
                node_id=str(node_id),
                parent_node_id=raw.get("parent_node_id"),
                depth=safe_int(raw.get("depth", 0), 0),
                node_kind=raw.get("node_kind"),
                path_from_root=[str(n) for n in path_from_root],
                is_math_heavy=bool(raw.get("is_math_heavy", False)),
                is_expanded=bool(raw.get("is_expanded", False)),
                status=graph_meta.get("status"),
                score=safe_float(scores.get(node_id), None),
                attempts=safe_int(graph_meta.get("attempts", 0), 0)
                if graph_meta
                else 0,
            )
        )
    out.sort(
        key=lambda item: (item.depth if item.depth is not None else 0, item.node_id)
    )
    return out


def build_option_metadata(
    values: dict, options: list[str]
) -> dict[str, dict[str, Any]]:
    """Return per-option hierarchy metadata keyed by node ID."""
    return {node: get_node_meta(values, node) for node in options}


# ── Feature flags ─────────────────────────────────────────────


def is_journey_v2_enabled(values: dict) -> bool:
    return bool(values.get("journey_orchestrator_v2", False))


def resolve_journey_orchestrator_v2(user_id: int, seed_value: str, *, settings) -> bool:
    """Deterministic rollout gate for the v2 journey orchestrator."""
    if not settings.journey_orchestrator_v2_enabled:
        return False

    allowlist_raw = (settings.journey_orchestrator_v2_allowlist_user_ids or "").strip()
    if allowlist_raw:
        allowlist = {
            int(token.strip())
            for token in allowlist_raw.split(",")
            if token.strip().isdigit()
        }
        if user_id in allowlist:
            return True

    rollout = max(0, min(int(settings.journey_orchestrator_v2_rollout_percent), 100))
    if rollout <= 0:
        return False

    seed = f"{user_id}:{seed_value}"
    bucket = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 100
    return bucket < rollout


# ── Idempotency fingerprint ──────────────────────────────────


def build_continue_fingerprint(
    values: dict, waiting_on: list[str], req: ContinueRequest
) -> str:
    """SHA-256 digest that uniquely identifies a continue-request's intent."""
    normalized = {
        "current_node": str(values.get("current_node", "") or ""),
        "journey_mode": normalize_journey_mode(values.get("journey_mode")),
        "waiting_on": sorted(waiting_on),
        "answers": req.answers if isinstance(req.answers, list) else None,
        "selected_node": str(req.selected_node or "").strip() or None,
        "traversal_mode": normalize_traversal_mode(
            req.traversal_mode or values.get("traversal_mode")
        ),
        "eval_action": (
            values.get("evaluation", {}).get("next_action")
            if isinstance(values.get("evaluation"), dict)
            else None
        ),
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── UX state-machine payload builder ──────────────────────────


def build_next_action_payload(
    *,
    session_id: str,
    session_status: str,
    values: dict,
    waiting_on: list[str],
    recommend_fn,
) -> dict:
    """
    Assemble a dict describing the next CTA for the frontend.

    *recommend_fn* is injected to avoid a circular import with the
    recommendation service.
    """
    current_node = str(values.get("current_node", "") or "")
    journey_mode = normalize_journey_mode(values.get("journey_mode"))
    traversal_mode = normalize_traversal_mode(values.get("traversal_mode"))
    v2_enabled = is_journey_v2_enabled(values)
    previous_node = derive_previous_node(values)
    can_go_back = bool(previous_node and "next" in waiting_on and v2_enabled)
    options = derive_available_choices(
        values, waiting_on=waiting_on, enable_backtracking=v2_enabled
    )
    forward_options = derive_forward_choices(values)
    recommendation = recommend_fn(values, forward_options, traversal_mode)
    node_meta = get_node_meta(values, current_node)

    hierarchy_payload = {
        "parent_node_id": node_meta.get("parent_node_id"),
        "depth": node_meta.get("depth"),
        "node_kind": node_meta.get("node_kind"),
        "path_from_root": node_meta.get("path_from_root", []),
        "is_math_heavy": node_meta.get("is_math_heavy"),
        "is_expanded": node_meta.get("is_expanded"),
        "option_metadata": build_option_metadata(values, options),
    }

    # ── Status-based early returns ────────────────────────────
    if session_status in {"initializing", "running", "evaluating"}:
        return {
            "session_id": session_id,
            "action": "wait",
            "status": "waiting",
            "message": f"Session is '{session_status}'. Wait for readiness.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }
    if session_status == "completed":
        return {
            "session_id": session_id,
            "action": "completed",
            "status": "completed",
            "message": "Learning journey completed.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }
    if session_status in {"archived", "error"}:
        return {
            "session_id": session_id,
            "action": "blocked",
            "status": "blocked",
            "message": f"Session is '{session_status}' and cannot continue.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": [],
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": None,
            "recommendation_reason": None,
            "recommendation_factors": {},
            "required_input": None,
            **hierarchy_payload,
        }

    # ── Graph-interrupt based actions ─────────────────────────
    if "evaluator" in waiting_on:
        return {
            "session_id": session_id,
            "action": "take_quiz",
            "status": "ready",
            "message": "Submit quiz answers to continue. Optionally preselect your next branch.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": options,
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": recommendation["node"],
            "recommendation_reason": recommendation["reason"],
            "recommendation_factors": recommendation["factors"],
            "required_input": "answers",
            **hierarchy_payload,
        }

    evaluation = values.get("evaluation", {})
    completed_eval = (
        isinstance(evaluation, dict) and evaluation.get("next_action") == "completed"
    )
    if {"next", "bridge"} & set(waiting_on) or completed_eval:
        if "bridge" in waiting_on and "next" not in waiting_on:
            return {
                "session_id": session_id,
                "action": "advance_remediation",
                "status": "ready",
                "message": "Advance to remediation step.",
                "current_node": current_node,
                "waiting_on": waiting_on,
                "options": [],
                "traversal_mode": traversal_mode,
                "journey_mode": journey_mode,
                "can_go_back": can_go_back,
                "previous_node": previous_node if v2_enabled else None,
                "recommended_node": None,
                "recommendation_reason": None,
                "recommendation_factors": {},
                "required_input": None,
                **hierarchy_payload,
            }
        return {
            "session_id": session_id,
            "action": "choose_branch" if options else "advance",
            "status": "ready",
            "message": "Choose your next branch or continue with the recommended option.",
            "current_node": current_node,
            "waiting_on": waiting_on,
            "options": options,
            "traversal_mode": traversal_mode,
            "journey_mode": journey_mode,
            "can_go_back": can_go_back,
            "previous_node": previous_node if v2_enabled else None,
            "recommended_node": recommendation["node"],
            "recommendation_reason": recommendation["reason"],
            "recommendation_factors": recommendation["factors"],
            "required_input": "selected_node" if options else None,
            **hierarchy_payload,
        }

    # ── Fallback: no actionable interrupt ─────────────────────
    return {
        "session_id": session_id,
        "action": "wait",
        "status": "ready",
        "message": "No immediate action required. Refresh state shortly.",
        "current_node": current_node,
        "waiting_on": waiting_on,
        "options": options,
        "traversal_mode": traversal_mode,
        "journey_mode": journey_mode,
        "can_go_back": can_go_back,
        "previous_node": previous_node if v2_enabled else None,
        "recommended_node": recommendation["node"],
        "recommendation_reason": recommendation["reason"],
        "recommendation_factors": recommendation["factors"],
        "required_input": None,
        **hierarchy_payload,
    }


# ── Choice derivation ────────────────────────────────────────


def derive_forward_choices(values: dict) -> list[str]:
    """Compute the set of forward-only traversal choices from graph state."""
    frontier = values.get("active_frontier", [])
    if isinstance(frontier, list):
        mastery = values.get("mastery", {})
        if not isinstance(mastery, dict):
            mastery = {}
        current_node = str(values.get("current_node", "") or "")
        front_choices: list[str] = []
        for node in frontier:
            normalized = str(node).strip()
            if (
                not normalized
                or normalized == current_node
                or mastery.get(normalized, False)
            ):
                continue
            if normalized not in front_choices:
                front_choices.append(normalized)
        if front_choices:
            return front_choices

    raw_choices = values.get("available_choices", [])
    if isinstance(raw_choices, list):
        choices: list[str] = []
        for item in raw_choices:
            node = str(item).strip()
            if node and node not in choices:
                choices.append(node)
        if choices:
            return choices

    subtopics = values.get("subtopics", [])
    mastery = values.get("mastery", {})
    current_node = str(values.get("current_node", "") or "")
    if not isinstance(subtopics, list):
        return []
    if not isinstance(mastery, dict):
        mastery = {}

    return [
        s
        for st in subtopics
        if (s := str(st).strip()) and s != current_node and not mastery.get(s, False)
    ]


def derive_available_choices(
    values: dict,
    waiting_on: list[str] | None = None,
    enable_backtracking: bool = False,
) -> list[str]:
    """Forward choices, optionally including the previous node for backtracking."""
    choices = list(derive_forward_choices(values))
    waiting_on = waiting_on or []
    if "next" not in waiting_on or not enable_backtracking:
        return choices

    previous_node = derive_previous_node(values)
    current_node = str(values.get("current_node", "") or "")
    if previous_node and previous_node != current_node and previous_node not in choices:
        choices.append(previous_node)
    return choices


def derive_previous_node(values: dict) -> str | None:
    """Walk the navigation stack / history to find the most recent prior node."""
    navigation_stack = values.get("navigation_stack", [])
    current_node = str(values.get("current_node", "") or "")
    if isinstance(navigation_stack, list):
        compact = [s for node in navigation_stack if (s := str(node).strip())]
        if compact:
            if compact[-1] != current_node:
                compact.append(current_node)
            if len(compact) >= 2:
                candidate = compact[-2]
                if candidate and candidate != current_node:
                    return candidate

    history = values.get("history", [])
    if not isinstance(history, list):
        return None

    for entry in reversed(history):
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "transition":
            node = str(entry.get("from_node", "")).strip()
            if node and node != current_node:
                return node
        if entry.get("type") in {"evaluation", "review_evaluation"}:
            node = str(entry.get("subtopic", "")).strip()
            if node and node != current_node:
                return node
    return None
