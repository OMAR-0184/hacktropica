from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agent.nodes.next_node import next_node_generator
from agent.nodes.orchestrator import orchestrator_node
from agent.nodes.quiz import _build_lesson_context
from agent.nodes.evaluator import evaluator_node
from api.main import app
from api.services import evaluation_service
from api.services.bullmq_client import BullMQClient
from api.database.model import User
from api.schemas.learning import ContinueRequest
from api.services.graph_helpers import build_continue_fingerprint
from api.services import concurrency


def test_quiz_context_uses_generated_markdown_lesson() -> None:
    context = _build_lesson_context(
        "## Binary search\nIt halves a sorted search interval each step."
    )
    assert "Binary search" in context
    assert "halves a sorted search interval" in context


@pytest.mark.asyncio
async def test_failed_evaluation_does_not_mark_node_mastered() -> None:
    state = {
        "current_node": "Intro to Python",
        "subtopics": ["Intro to Python"],
        "graph_nodes": {"Intro to Python": {"status": "unlocked"}},
        "node_catalog": {"Intro to Python": {"path_from_root": ["Intro to Python"]}},
        "mastery": {},
        "history": [],
        "evaluation": {"passed": False, "next_action": "completed"},
    }
    result = await next_node_generator(state)
    assert result["mastery"].get("Intro to Python") is not True
    assert result["graph_nodes"]["Intro to Python"]["status"] != "mastered"


@pytest.mark.asyncio
async def test_failed_final_evaluation_is_not_recorded_as_mastery() -> None:
    result = await evaluator_node({
        "current_node": "Basics",
        "subtopics": ["Basics"],
        "graph_nodes": {"Basics": {"status": "unlocked", "attempts": 0}},
        "node_catalog": {"Basics": {"depth": 0, "node_kind": "intro", "path_from_root": ["Basics"]}},
        "quiz": {
            "questions": [{
                "question_id": "q1", "question": "Which answer is correct?",
                "options": ["A", "B"], "correct_index": 0, "concept": "Basics",
            }],
            "question_count": 1,
        },
        "evaluation": {"user_answers": [1]},
        "remediation_count": 3,
        "history": [],
    })
    assert result["evaluation"]["passed"] is False
    assert result["evaluation"]["next_action"] == "completed"
    assert result["mastery"].get("Basics") is not True
    assert result["graph_nodes"]["Basics"]["status"] != "mastered"


@pytest.mark.asyncio
async def test_orchestrator_obeys_evaluator_remediation_limit(monkeypatch) -> None:
    async def unexpected_llm_call(**kwargs):
        raise AssertionError("deterministic evaluator action should bypass the LLM")

    monkeypatch.setattr("agent.nodes.orchestrator.invoke_llm_json", unexpected_llm_call)
    result = await orchestrator_node({
        "current_node": "Basics",
        "evaluation": {"score": 0.2, "passed": False, "next_action": "next_topic"},
    })
    assert result["orchestrator_history"][-1]["decision"] == "next"


@pytest.mark.asyncio
async def test_quiz_endpoint_rejects_stale_quiz(monkeypatch) -> None:
    async def state_snapshot(session_id):
        return SimpleNamespace(values={
            "current_node": "New node",
            "quiz": {"node_id": "Old node", "questions": []},
        })

    monkeypatch.setattr(evaluation_service, "get_current_state", state_snapshot)
    with pytest.raises(HTTPException) as exc:
        await evaluation_service.get_quiz(
            session_id="session-1", db_session=SimpleNamespace(status="ready")
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_bullmq_client_adds_stable_job_with_retry_policy(monkeypatch) -> None:
    import api.services.bullmq_client as bullmq_client

    observed = {}

    class Queue:
        def __init__(self, name, options):
            observed["queue"] = name
            observed["connection"] = options["connection"]

        async def getJob(self, job_id):
            observed["job_id"] = job_id
            return None

        async def add(self, name, data, options):
            observed.update(name=name, data=data, options=options)
            return SimpleNamespace(id=options["jobId"])

    monkeypatch.setattr(bullmq_client, "Queue", Queue)
    client = BullMQClient("redis://redis:6379/0")
    job_id = await client.enqueue_job(
        "advance_learning_task", "session-1", job_id="advance:session-1:req-1"
    )
    assert job_id == observed["job_id"]
    assert observed["queue"] == "cognimap-learning"
    assert observed["connection"] == "redis://redis:6379/0"
    assert observed["name"] == "advance_learning_task"
    assert observed["data"] == {"args": ["session-1"]}
    assert observed["options"]["attempts"] == 3
    assert observed["options"]["backoff"] == {"type": "exponential", "delay": 1000}


def test_idempotency_fingerprint_changes_between_node_attempts() -> None:
    request = ContinueRequest(answers=[0], client_request_id=None)
    first = build_continue_fingerprint(
        {"current_node": "Basics", "graph_nodes": {"Basics": {"attempts": 0}}},
        ["evaluator"],
        request,
    )
    later_attempt = build_continue_fingerprint(
        {"current_node": "Basics", "graph_nodes": {"Basics": {"attempts": 1}}},
        ["evaluator"],
        request,
    )
    assert first != later_attempt


@pytest.mark.asyncio
async def test_authentication_cache_failure_falls_back_to_database(monkeypatch) -> None:
    import api.routers.auth as auth

    user = User(id=7, email="learner@example.com", username="learner")

    class Redis:
        async def get(self, key):
            raise ConnectionError("redis unavailable")

    class Result:
        class Scalars:
            def first(self):
                return user

        def scalars(self):
            return self.Scalars()

    class DB:
        async def execute(self, query):
            return Result()

    monkeypatch.setattr(auth.jwt, "decode", lambda *args, **kwargs: {"sub": user.email, "type": "access"})
    monkeypatch.setattr(auth, "get_redis", lambda: Redis())
    actual = await auth.get_current_user("token", DB())
    assert actual.id == user.id


@pytest.mark.asyncio
async def test_progression_lock_fails_closed_when_redis_is_down(monkeypatch) -> None:
    class Redis:
        async def set(self, *args, **kwargs):
            raise ConnectionError("redis unavailable")

    monkeypatch.setattr(concurrency, "get_redis", lambda: Redis())
    with pytest.raises(HTTPException) as exc:
        await concurrency.acquire_progression_lock("session-1")
    assert exc.value.status_code == 503


def test_every_documented_learning_endpoint_is_auth_gated() -> None:
    """Smoke every REST learning endpoint without requiring database services."""
    paths = app.openapi()["paths"]
    client = TestClient(app)
    learning_paths = {
        path: methods for path, methods in paths.items() if path.startswith("/learning/")
    }
    assert len(learning_paths) >= 20

    for path, methods in learning_paths.items():
        concrete_path = path.replace("{session_id}", "session-test").replace(
            "{node_id}", "node-test"
        )
        for method in methods:
            payload = None
            if method == "post":
                if path.endswith("/start"):
                    payload = {"topic": "Python"}
                elif path.endswith("/evaluate"):
                    payload = {"answers": [0]}
                elif path.endswith("/nodes"):
                    payload = {"node_id": "custom-node"}
                else:
                    payload = {}
            response = client.request(method.upper(), concrete_path, json=payload)
            assert response.status_code == 401, (
                method, path, response.status_code, response.text
            )


@pytest.mark.asyncio
async def test_python_worker_dispatches_learning_job(monkeypatch) -> None:
    from api.engine import worker

    seen = {}

    async def run_serially(session_id, operation):
        seen["session_id"] = session_id
        return await operation()

    async def fake_run(**kwargs):
        seen.update(kwargs)
        return True

    monkeypatch.setattr(worker, "_run_session_serially", run_serially)
    monkeypatch.setattr(worker, "run_learning_graph", fake_run)
    result = await worker.process_job(
        SimpleNamespace(
            name="start_learning_task",
            data={"args": ["session-1", "Python", "detailed", "bfs", "", False]},
        ),
        "job-token",
    )
    assert result == {"status": "completed"}
    assert seen["session_id"] == "session-1"
    assert seen["traversal_mode"] == "bfs"


def test_root_and_health_endpoints(monkeypatch) -> None:
    import api.main as main_module

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def execute(self, statement):
            return None

    class Redis:
        async def ping(self):
            return True

    class Queue:
        async def ping(self):
            return True

    monkeypatch.setattr(
        main_module, "engine", SimpleNamespace(connect=lambda: Connection())
    )
    monkeypatch.setattr(main_module, "get_redis", lambda: Redis())
    monkeypatch.setattr(main_module, "get_queue_client", lambda: Queue())
    client = TestClient(app)
    assert client.get("/").status_code == 200
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["queue"] == "ok"


def test_public_auth_endpoints_validate_payloads() -> None:
    client = TestClient(app)
    assert client.post("/auth/register", json={}).status_code == 422
    assert client.post("/auth/login/json", json={}).status_code == 422
    assert client.post("/auth/refresh", json={}).status_code == 422
    assert client.get("/auth/profile").status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_websocket_requires_authentication() -> None:
    from starlette.websockets import WebSocketDisconnect

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/learning/session-test/stream"):
            pass
    assert exc.value.code == 4001
