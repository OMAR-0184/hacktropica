from __future__ import annotations

from enum import Enum


class NodeStatus(str, Enum):
    """Lifecycle status of a learning curriculum node."""

    LOCKED = "locked"
    UNLOCKED = "unlocked"
    ACTIVE = "active"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"


class EvaluationNextAction(str, Enum):
    """Next action decided after grading an evaluation."""

    NEXT_TOPIC = "next_topic"
    REMEDIATION = "remediation"
    COMPLETED = "completed"
    PENDING = "pending"


class OrchestratorAction(str, Enum):
    """Actions the dynamic routing orchestrator can select."""

    LESSON_GENERATOR = "lesson_generator"
    QUIZ = "quiz"
    EVALUATOR = "evaluator"
    BRIDGE = "bridge"
    NEXT = "next"
    END = "__end__"


class NodeKind(str, Enum):
    """Pedagogical classification of a node."""

    INTRO = "intro"
    CONCEPT = "concept"
    ADVANCED = "advanced"
    REMEDIATION = "remediation"


class TraversalMode(str, Enum):
    """Curriculum graph traversal strategy."""

    BFS = "bfs"
    DFS = "dfs"


class JourneyMode(str, Enum):
    """Current modality of the user's journey."""

    LEARN = "learn"
    REVIEW = "review"


# Valid node status transitions
VALID_NODE_TRANSITIONS: dict[NodeStatus, set[NodeStatus]] = {
    NodeStatus.LOCKED: {NodeStatus.UNLOCKED, NodeStatus.ACTIVE},
    NodeStatus.UNLOCKED: {NodeStatus.ACTIVE, NodeStatus.MASTERED, NodeStatus.NEEDS_REVIEW},
    NodeStatus.ACTIVE: {NodeStatus.MASTERED, NodeStatus.NEEDS_REVIEW, NodeStatus.UNLOCKED},
    NodeStatus.NEEDS_REVIEW: {NodeStatus.ACTIVE, NodeStatus.MASTERED, NodeStatus.UNLOCKED},
    NodeStatus.MASTERED: {NodeStatus.ACTIVE, NodeStatus.NEEDS_REVIEW},  # Reviewing a mastered node
}


def can_transition_node(from_status: str | NodeStatus, to_status: str | NodeStatus) -> bool:
    """Check whether a node status transition is valid."""
    try:
        source = NodeStatus(from_status)
        target = NodeStatus(to_status)
    except ValueError:
        return False

    if source == target:
        return True
    return target in VALID_NODE_TRANSITIONS.get(source, set())
