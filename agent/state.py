"""
Central state schema for the Cognimap learning graph.

Every node receives the full state and returns a partial dict
of only the keys it wants to update (immutable-update pattern).
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class SubtopicMeta(TypedDict, total=False):
    """Metadata tracked per subtopic node."""

    status: str
    attempts: int
    best_score: float


class NodeCatalogEntry(TypedDict, total=False):
    """Hierarchy metadata for each learning/remediation node."""

    node_id: str
    parent_node_id: str | None
    depth: int
    node_kind: Literal["intro", "concept", "advanced", "remediation"]
    path_from_root: list[str]
    is_math_heavy: bool
    is_expanded: bool


class CognimapState(TypedDict, total=False):
    """Root state flowing through every node in the graph."""

    topic: str
    learner_profile: str
    course_mode: str  # "detailed" or "micro"
    subtopics: list[str]
    current_node: str

    graph_nodes: dict[str, SubtopicMeta]
    node_catalog: dict[str, NodeCatalogEntry]
    parent_map: dict[str, str | None]
    children_map: dict[str, list[str]]
    expanded_nodes: list[str]
    active_frontier: list[str]
    current_path: list[str]
    available_choices: list[str]
    selected_next_node: str
    traversal_mode: Literal["bfs", "dfs"]
    navigation_stack: list[str]
    journey_mode: Literal["learn", "review"]
    journey_orchestrator_v2: bool

    history: list[dict[str, Any]]

    scores: dict[str, float]
    weak_areas: dict[str, list[str]]
    mastery: dict[str, bool]

    lesson: dict[str, Any]

    quiz: dict[str, Any]

    evaluation: dict[str, Any]

    remediation_count: int
