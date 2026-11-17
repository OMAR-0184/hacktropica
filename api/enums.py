from __future__ import annotations

import logging
from enum import Enum
from typing import Set

from agent.enums import (
    NodeStatus,
    EvaluationNextAction,
    OrchestratorAction,
    NodeKind,
    TraversalMode,
    JourneyMode,
)

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Lifecycle status of a learning session."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    READY = "ready"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ERROR = "error"
    ARCHIVED = "archived"


class SessionPhase(str, Enum):
    """Current execution phase of the session in the agent pipeline."""

    ROOT = "root"
    LESSON = "lesson"
    EVALUATOR = "evaluator"
    ADVANCING = "advancing"
    COMPLETED = "completed"


class JourneyAction(str, Enum):
    """Next logical step/call-to-action presented to the learner."""

    WAIT = "wait"
    TAKE_QUIZ = "take_quiz"
    ADVANCE = "advance"
    ADVANCE_REMEDIATION = "advance_remediation"
    CHOOSE_BRANCH = "choose_branch"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SUBMIT_EVALUATION = "submit_evaluation"


class JourneyStepStatus(str, Enum):
    """Progress status returned in ContinueResponse and NextActionResponse."""

    WAITING = "waiting"
    READY = "ready"
    NEEDS_INPUT = "needs_input"
    PROCESSING = "processing"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""

    def __init__(self, current_state: str, new_state: str, entity: str = "Session"):
        self.current_state = current_state
        self.new_state = new_state
        self.entity = entity
        super().__init__(
            f"Invalid {entity} transition: cannot transition from '{current_state}' to '{new_state}'"
        )


# Valid directed transitions for SessionStatus
VALID_SESSION_TRANSITIONS: dict[SessionStatus, Set[SessionStatus]] = {
    SessionStatus.INITIALIZING: {
        SessionStatus.RUNNING,
        SessionStatus.ERROR,
        SessionStatus.ARCHIVED,
    },
    SessionStatus.RUNNING: {
        SessionStatus.READY,
        SessionStatus.COMPLETED,
        SessionStatus.ERROR,
        SessionStatus.ARCHIVED,
    },
    SessionStatus.READY: {
        SessionStatus.RUNNING,
        SessionStatus.EVALUATING,
        SessionStatus.COMPLETED,
        SessionStatus.ERROR,
        SessionStatus.ARCHIVED,
    },
    SessionStatus.EVALUATING: {
        SessionStatus.READY,
        SessionStatus.COMPLETED,
        SessionStatus.ERROR,
        SessionStatus.ARCHIVED,
    },
    SessionStatus.COMPLETED: {
        SessionStatus.ARCHIVED,
        SessionStatus.ERROR,
    },
    SessionStatus.ERROR: {
        SessionStatus.RUNNING,  # Allow retry
        SessionStatus.ARCHIVED,
    },
    SessionStatus.ARCHIVED: set(),  # Terminal state
}


class SessionStateMachine:
    """Explicit state machine managing session lifecycle transitions."""

    @staticmethod
    def can_transition(
        from_status: str | SessionStatus | None, to_status: str | SessionStatus
    ) -> bool:
        if from_status is None:
            return True
        try:
            source = SessionStatus(from_status)
            target = SessionStatus(to_status)
        except ValueError:
            return False

        if source == target:
            return True
        return target in VALID_SESSION_TRANSITIONS.get(source, set())

    @classmethod
    def transition(
        cls,
        from_status: str | SessionStatus | None,
        to_status: str | SessionStatus,
        *,
        session_id: str | None = None,
        enforce: bool = True,
    ) -> SessionStatus:
        """Validate and return the new SessionStatus, raising InvalidStateTransitionError if illegal."""
        target = SessionStatus(to_status)
        if from_status is None:
            return target

        try:
            source = SessionStatus(from_status)
        except ValueError:
            logger.warning(
                "Encountered unknown source session status '%s' for session %s",
                from_status,
                session_id,
            )
            return target

        if source == target:
            return target

        if not cls.can_transition(source, target):
            msg = f"Cannot transition session from '{source.value}' to '{target.value}'"
            if session_id:
                msg += f" (session_id={session_id})"
            logger.warning(msg)
            if enforce:
                raise InvalidStateTransitionError(source.value, target.value, entity="Session")

        return target


__all__ = [
    "SessionStatus",
    "SessionPhase",
    "JourneyAction",
    "JourneyStepStatus",
    "NodeStatus",
    "EvaluationNextAction",
    "OrchestratorAction",
    "NodeKind",
    "TraversalMode",
    "JourneyMode",
    "InvalidStateTransitionError",
    "VALID_SESSION_TRANSITIONS",
    "SessionStateMachine",
]
