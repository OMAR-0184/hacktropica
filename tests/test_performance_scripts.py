from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from scripts import common, concurrency_test, performance_test


def test_safe_target_removes_credentials_query_and_fragment() -> None:
    target = common.safe_target(
        "https://learner:secret@example.test:8443/health?token=private#section"
    )
    assert target == "https://example.test:8443/health"


def test_summarize_calculates_latency_throughput_and_failures() -> None:
    results = [
        {"latency_seconds": 0.01, "status_code": 200, "bytes_received": 8, "success": True, "error_type": None},
        {"latency_seconds": 0.02, "status_code": 204, "bytes_received": 0, "success": True, "error_type": None},
        {"latency_seconds": 0.03, "status_code": 503, "bytes_received": 12, "success": False, "error_type": None},
        {"latency_seconds": 0.04, "status_code": None, "bytes_received": 0, "success": False, "error_type": "ReadTimeout"},
    ]

    metrics = common.summarize(
        results,
        2.0,
        configured_concurrency=4,
        observed_max_in_flight=3,
    )

    assert metrics["request_count"] == 4
    assert metrics["successful_requests"] == 2
    assert metrics["failed_requests"] == 2
    assert metrics["requests_per_second"] == 2.0
    assert metrics["latency_ms"]["p50"] == pytest.approx(25.0)
    assert metrics["latency_ms"]["p95"] == pytest.approx(38.5)
    assert metrics["status_codes"] == {"200": 1, "204": 1, "503": 1}
    assert metrics["transport_errors"] == {"ReadTimeout": 1}
    assert metrics["observed_max_in_flight"] == 3


def test_record_result_appends_runs(tmp_path) -> None:
    output = tmp_path / "results.json"
    common.record_result(output, {"test": "first"})
    common.record_result(output, {"test": "second"})

    document = json.loads(output.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    assert document["runs"] == [{"test": "first"}, {"test": "second"}]


def _fake_httpx(monkeypatch: pytest.MonkeyPatch, module, delay: float = 0.01):
    tracker = {"active": 0, "peak": 0}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url: str):
            tracker["active"] += 1
            tracker["peak"] = max(tracker["peak"], tracker["active"])
            try:
                await asyncio.sleep(delay)
                return SimpleNamespace(status_code=200, content=b"healthy")
            finally:
                tracker["active"] -= 1

    class FakeLimits:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_httpx = SimpleNamespace(
        AsyncClient=lambda **kwargs: FakeClient(),
        Timeout=lambda seconds: seconds,
        Limits=FakeLimits,
        InvalidURL=ValueError,
    )
    monkeypatch.setattr(module, "httpx", fake_httpx)
    return tracker


def test_performance_script_records_sequential_requests(monkeypatch, tmp_path) -> None:
    tracker = _fake_httpx(monkeypatch, performance_test)
    args = SimpleNamespace(
        url="http://api.test/health",
        timeout=1.0,
        header=[],
        iterations=4,
        warmup=1,
        output=tmp_path / "results.json",
    )

    run, passed = asyncio.run(performance_test.run(args))

    assert passed is True
    assert tracker["peak"] == 1
    assert run["metrics"]["request_count"] == 4
    assert run["metrics"]["warmup_requests"] == 1
    assert json.loads(args.output.read_text(encoding="utf-8"))["runs"] == [run]


def test_concurrency_script_respects_concurrency_limit(monkeypatch, tmp_path) -> None:
    tracker = _fake_httpx(monkeypatch, concurrency_test)
    args = SimpleNamespace(
        url="http://api.test/health",
        timeout=1.0,
        header=[],
        requests=8,
        concurrency=3,
        warmup=0,
        output=tmp_path / "results.json",
    )

    run, passed = asyncio.run(concurrency_test.run(args))

    assert passed is True
    assert tracker["peak"] == 3
    assert run["metrics"]["request_count"] == 8
    assert run["metrics"]["configured_concurrency"] == 3
    assert run["metrics"]["observed_max_in_flight"] == 3
