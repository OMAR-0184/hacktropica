"""Tests for explicit state machines and arq task queue migration."""

from __future__ import annotations

from types import SimpleNamespace
import pytest

from agent.enums import (
    EvaluationNextAction,
    JourneyMode,
    NodeKind,
    NodeStatus,
    OrchestratorAction,
    TraversalMode,
    can_transition_node,
)
from api.database.model import NodeState, Session
from api.enums import (
    InvalidStateTransitionError,
    JourneyAction,
    JourneyStepStatus,
    SessionPhase,
    SessionStateMachine,
    SessionStatus,
)
from api.services.task_queue import (
    ALLOWED_JOBS,
    QUEUE_NAME,
    BullMQClient,
    TaskQueueClient,
)
from api.engine.worker import (
    WorkerSettings,
    advance_learning_task,
    process_job,
    resume_learning_task,
    start_learning_task,
)


class TestSessionStateMachine:
    """Verify directed transitions and invariant enforcement for SessionStatus."""

    def test_valid_transitions_from_initializing(self):
        assert SessionStateMachine.can_transition(SessionStatus.INITIALIZING, SessionStatus.RUNNING)
        assert SessionStateMachine.can_transition(SessionStatus.INITIALIZING, SessionStatus.ERROR)
        assert SessionStateMachine.can_transition(SessionStatus.INITIALIZING, SessionStatus.ARCHIVED)
        # Cannot transition directly from INITIALIZING to READY or COMPLETED
        assert not SessionStateMachine.can_transition(SessionStatus.INITIALIZING, SessionStatus.READY)
        assert not SessionStateMachine.can_transition(SessionStatus.INITIALIZING, SessionStatus.COMPLETED)

    def test_valid_transitions_from_running(self):
        assert SessionStateMachine.can_transition(SessionStatus.RUNNING, SessionStatus.READY)
        assert SessionStateMachine.can_transition(SessionStatus.RUNNING, SessionStatus.COMPLETED)
        assert SessionStateMachine.can_transition(SessionStatus.RUNNING, SessionStatus.ERROR)
        assert SessionStateMachine.can_transition(SessionStatus.RUNNING, SessionStatus.ARCHIVED)
        assert not SessionStateMachine.can_transition(SessionStatus.RUNNING, SessionStatus.EVALUATING)

    def test_valid_transitions_from_ready(self):
        assert SessionStateMachine.can_transition(SessionStatus.READY, SessionStatus.RUNNING)
        assert SessionStateMachine.can_transition(SessionStatus.READY, SessionStatus.EVALUATING)
        assert SessionStateMachine.can_transition(SessionStatus.READY, SessionStatus.COMPLETED)
        assert SessionStateMachine.can_transition(SessionStatus.READY, SessionStatus.ARCHIVED)
        assert SessionStateMachine.can_transition(SessionStatus.READY, SessionStatus.ERROR)

    def test_valid_transitions_from_evaluating(self):
        assert SessionStateMachine.can_transition(SessionStatus.EVALUATING, SessionStatus.READY)
        assert SessionStateMachine.can_transition(SessionStatus.EVALUATING, SessionStatus.COMPLETED)
        assert SessionStateMachine.can_transition(SessionStatus.EVALUATING, SessionStatus.ERROR)
        assert not SessionStateMachine.can_transition(SessionStatus.EVALUATING, SessionStatus.RUNNING)

    def test_archived_is_terminal(self):
        for status in SessionStatus:
            if status != SessionStatus.ARCHIVED:
                assert not SessionStateMachine.can_transition(SessionStatus.ARCHIVED, status)

    def test_transition_enforcement_raises_on_invalid(self):
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            SessionStateMachine.transition(SessionStatus.ARCHIVED, SessionStatus.RUNNING, enforce=True)
        assert "cannot transition from 'archived' to 'running'" in str(exc_info.value)

    def test_same_state_transition_is_noop(self):
        result = SessionStateMachine.transition(SessionStatus.READY, SessionStatus.READY)
        assert result == SessionStatus.READY

    def test_session_model_properties_and_methods(self):
        session = Session(id="s1", status=SessionStatus.INITIALIZING.value)
        assert session.parsed_status == SessionStatus.INITIALIZING
        assert session.can_transition_to(SessionStatus.RUNNING)
        assert not session.can_transition_to(SessionStatus.COMPLETED)


class TestNodeStateMachine:
    """Verify directed transitions and invariants for NodeStatus."""

    def test_valid_node_transitions(self):
        assert can_transition_node(NodeStatus.LOCKED, NodeStatus.UNLOCKED)
        assert can_transition_node(NodeStatus.UNLOCKED, NodeStatus.ACTIVE)
        assert can_transition_node(NodeStatus.ACTIVE, NodeStatus.MASTERED)
        assert can_transition_node(NodeStatus.ACTIVE, NodeStatus.NEEDS_REVIEW)
        assert can_transition_node(NodeStatus.NEEDS_REVIEW, NodeStatus.ACTIVE)
        assert can_transition_node(NodeStatus.NEEDS_REVIEW, NodeStatus.MASTERED)
        assert can_transition_node(NodeStatus.MASTERED, NodeStatus.ACTIVE)

    def test_invalid_node_transitions(self):
        assert not can_transition_node(NodeStatus.LOCKED, NodeStatus.MASTERED)
        assert not can_transition_node("invalid_status", NodeStatus.ACTIVE)

    def test_node_state_model_property(self):
        node = NodeState(node_id="n1", status=NodeStatus.UNLOCKED.value)
        assert node.parsed_status == NodeStatus.UNLOCKED


class TestEnumsIntegrity:
    """Verify all enums have expected values and string representations."""

    def test_evaluation_next_action_values(self):
        assert EvaluationNextAction.NEXT_TOPIC.value == "next_topic"
        assert EvaluationNextAction.REMEDIATION.value == "remediation"
        assert EvaluationNextAction.COMPLETED.value == "completed"
        assert EvaluationNextAction.PENDING.value == "pending"

    def test_orchestrator_action_values(self):
        expected = {"lesson_generator", "quiz", "evaluator", "bridge", "next", "__end__"}
        assert {a.value for a in OrchestratorAction} == expected

    def test_journey_action_values(self):
        assert JourneyAction.WAIT.value == "wait"
        assert JourneyAction.TAKE_QUIZ.value == "take_quiz"
        assert JourneyAction.ADVANCE.value == "advance"
        assert JourneyAction.CHOOSE_BRANCH.value == "choose_branch"
        assert JourneyAction.COMPLETED.value == "completed"
        assert JourneyAction.BLOCKED.value == "blocked"

    def test_journey_step_status_values(self):
        assert JourneyStepStatus.WAITING.value == "waiting"
        assert JourneyStepStatus.READY.value == "ready"
        assert JourneyStepStatus.NEEDS_INPUT.value == "needs_input"
        assert JourneyStepStatus.PROCESSING.value == "processing"


class TestArqTaskQueueClient:
    """Verify TaskQueueClient (and backward-compatible BullMQClient) using arq."""

    @pytest.mark.asyncio
    async def test_enqueue_valid_job_computes_stable_id(self, monkeypatch):
        observed = {}

        class MockArqPool:
            async def enqueue_job(self, name, *args, _job_id=None, _queue_name=None):
                observed.update(name=name, args=args, job_id=_job_id, queue_name=_queue_name)
                return SimpleNamespace(job_id=_job_id)

        client = TaskQueueClient("redis://localhost:6379/0")

        async def fake_pool():
            return MockArqPool()

        monkeypatch.setattr(client, "_get_pool", fake_pool)

        job_id = await client.enqueue_job("start_learning_task", "session-123", "Calculus")
        assert job_id.startswith("start_learning_task-")
        assert observed["name"] == "start_learning_task"
        assert observed["args"] == ("session-123", "Calculus")
        assert observed["queue_name"] == QUEUE_NAME

    @pytest.mark.asyncio
    async def test_enqueue_unsupported_job_raises_value_error(self):
        client = TaskQueueClient("redis://localhost:6379/0")
        with pytest.raises(ValueError) as exc:
            await client.enqueue_job("unsupported_job_name", "session-123")
        assert "Unsupported learning job" in str(exc.value)

    @pytest.mark.asyncio
    async def test_ping_invokes_redis_ping(self, monkeypatch):
        class MockArqPool:
            async def ping(self):
                return True

        client = TaskQueueClient("redis://localhost:6379/0")

        async def fake_pool():
            return MockArqPool()

        monkeypatch.setattr(client, "_get_pool", fake_pool)
        assert await client.ping() is True

    @pytest.mark.asyncio
    async def test_bullmq_compatibility_alias(self):
        assert BullMQClient is TaskQueueClient


class TestWorkerConfiguration:
    """Verify arq WorkerSettings and task handlers."""

    def test_worker_settings_registers_all_jobs(self):
        registered_names = {f.__name__ for f in WorkerSettings.functions}
        assert registered_names == ALLOWED_JOBS
        assert WorkerSettings.queue_name == QUEUE_NAME
        assert WorkerSettings.max_jobs == 10

    @pytest.mark.asyncio
    async def test_worker_functions_dispatch_serially(self, monkeypatch):
        dispatched = []

        async def fake_serial(session_id, op):
            dispatched.append(session_id)
            return await op()

        async def fake_graph(**kw):
            return True

        async def fake_resume(s, a):
            return True

        async def fake_advance(s):
            return True

        monkeypatch.setattr("api.engine.worker._run_session_serially", fake_serial)
        monkeypatch.setattr("api.engine.worker.run_learning_graph", fake_graph)
        monkeypatch.setattr("api.engine.worker.resume_graph_stream", fake_resume)
        monkeypatch.setattr("api.engine.worker.advance_graph_stream", fake_advance)

        ctx = {}
        await start_learning_task(ctx, "sess-1", "Linear Algebra")
        await resume_learning_task(ctx, "sess-2", [0, 1])
        await advance_learning_task(ctx, "sess-3")

        assert dispatched == ["sess-1", "sess-2", "sess-3"]
