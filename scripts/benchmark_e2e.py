"""
End-to-end benchmark for Cognimap learning cycles.

Runs a full register → session → (lesson → quiz → eval → next)×N flow,
measures per-step wall-clock times, and prints resume-ready metrics.

Usage:
    python -m scripts.benchmark_e2e --base-url http://127.0.0.1:8002
    python -m scripts.benchmark_e2e --cycles 2 --topic "Linear Algebra"
    python -m scripts.benchmark_e2e --concurrent-sessions 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import random
import string
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

# ── Defaults ──────────────────────────────────────────────────
DEFAULT_BASE = "http://127.0.0.1:8002"
DEFAULT_TOPIC = "Linear Algebra"
POLL_INTERVAL = 1.5          # seconds between workflow polls
POLL_TIMEOUT = 180.0         # max seconds to wait for agent
RESULTS_FILE = Path(__file__).resolve().parent / "results.json"


@dataclass
class StepTiming:
    """One measured step in a learning cycle."""
    step: str
    latency_s: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleResult:
    """Timings for a full lesson → quiz → eval cycle on one subtopic."""
    subtopic: str
    steps: list[StepTiming] = field(default_factory=list)

    @property
    def total_s(self) -> float:
        return sum(s.latency_s for s in self.steps)


@dataclass
class SessionResult:
    """All cycles within one session."""
    session_id: str
    topic: str
    setup_s: float = 0.0
    cycles: list[CycleResult] = field(default_factory=list)

    @property
    def total_s(self) -> float:
        return self.setup_s + sum(c.total_s for c in self.cycles)


# ── Helpers ───────────────────────────────────────────────────

def _random_tag() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def _timed(label: str, coro) -> tuple[Any, StepTiming]:
    """Run a coroutine and return (result, timing)."""
    t0 = time.perf_counter()
    result = await coro
    elapsed = time.perf_counter() - t0
    return result, StepTiming(step=label, latency_s=elapsed)


async def _poll_workflow(
    client: httpx.AsyncClient,
    session_id: str,
    *,
    predicate: Callable[[dict[str, Any]], bool] | None = None,
    timeout: float = POLL_TIMEOUT,
    label: str = "agent",
) -> dict[str, Any]:
    """Poll GET /learning/{id}/workflow until condition is met."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = await client.get(f"/learning/{session_id}/workflow")
        r.raise_for_status()
        snap = r.json()
        status = snap.get("status", "")
        action = snap.get("next_action", "wait")

        if predicate is not None:
            if predicate(snap):
                return snap
        else:
            if status not in ("initializing", "running", "evaluating") and action != "wait":
                return snap

        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(
        f"Workflow for session {session_id} timed out waiting for {label} after {timeout}s"
    )


# ── Core benchmark logic ─────────────────────────────────────

async def _register_and_login(client: httpx.AsyncClient) -> str:
    """Create a throwaway user and return the access token."""
    tag = _random_tag()
    email = f"bench_{tag}@example.com"
    username = f"bench_{tag}"
    password = "BenchmarkPass123!"

    # Register
    r = await client.post("/auth/register", json={
        "email": email,
        "password": password,
        "username": username,
    })
    r.raise_for_status()

    # Login to get tokens
    r = await client.post("/auth/login/json", json={
        "email": email,
        "password": password,
    })
    r.raise_for_status()
    return r.json()["access_token"]


async def _create_session(
    client: httpx.AsyncClient, topic: str, course_mode: str = "micro",
) -> str:
    """Create a learning session and return its id."""
    r = await client.post("/learning/start", json={
        "topic": topic,
        "course_mode": course_mode,
        "traversal_mode": "dfs",
    })
    r.raise_for_status()
    return r.json()["session_id"]


async def run_session(
    base_url: str,
    topic: str,
    course_mode: str,
    max_cycles: int,
    session_idx: int,
) -> SessionResult:
    """Run a full benchmark session: register, login, create, cycle through nodes."""
    timeout = httpx.Timeout(30.0, read=180.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:

        # ── Setup: register + login + create session ────
        t0 = time.perf_counter()
        token = await _register_and_login(client)
        client.headers["Authorization"] = f"Bearer {token}"
        session_id = await _create_session(client, topic, course_mode)
        setup_s = time.perf_counter() - t0

        result = SessionResult(session_id=session_id, topic=topic, setup_s=setup_s)
        print(f"  [session {session_idx}] created {session_id} ({setup_s:.2f}s setup)")

        # ── Learning cycles ─────────────────────────────
        for cycle_num in range(max_cycles):
            # Wait for agent to generate lesson & quiz
            t_wait = time.perf_counter()
            try:
                snap = await _poll_workflow(
                    client,
                    session_id,
                    predicate=lambda s: (
                        s.get("status") in ("ready", "completed", "error", "blocked")
                        and s.get("next_action") not in ("wait", None)
                    ),
                    label="lesson_and_quiz_ready",
                )
            except TimeoutError as e:
                print(f"  [session {session_idx}] ⏰ timeout waiting for agent: {e}")
                break

            wait_s = time.perf_counter() - t_wait
            action = snap.get("next_action", "")
            current = snap.get("current_node", "?")

            if action in ("completed", "blocked"):
                label = "completed" if action == "completed" else "blocked/error"
                print(f"  [session {session_idx}] ✓ session {label} after {cycle_num} cycles")
                break

            cycle = CycleResult(subtopic=current)
            cycle.steps.append(StepTiming(
                step="agent_lesson_generation", latency_s=wait_s,
            ))

            # ── take_quiz: lesson + quiz are both ready ─
            if action == "take_quiz":
                # Fetch lesson
                _, timing = await _timed(
                    "fetch_lesson",
                    client.get(f"/learning/{session_id}/lesson"),
                )
                cycle.steps.append(timing)

                # Fetch quiz
                resp, timing = await _timed(
                    "fetch_quiz",
                    client.get(f"/learning/{session_id}/quiz"),
                )
                cycle.steps.append(timing)
                resp.raise_for_status()

                # Generate random answers matching actual options
                quiz_data = resp.json()
                questions = quiz_data.get("questions", [])
                answers: list[int] = []
                for q in questions:
                    opts = q.get("options", [])
                    max_idx = max(0, len(opts) - 1)
                    answers.append(random.randint(0, max_idx))

                # Submit answers via /continue
                _, timing = await _timed(
                    "submit_answers",
                    client.post(
                        f"/learning/{session_id}/continue",
                        json={"answers": answers},
                    ),
                )
                cycle.steps.append(timing)

                # Wait for evaluation to complete
                t_eval = time.perf_counter()
                try:
                    snap = await _poll_workflow(
                        client,
                        session_id,
                        predicate=lambda s: (
                            s.get("evaluation_ready") is True
                            and s.get("status") in ("ready", "completed")
                            and s.get("next_action") != "take_quiz"
                        ),
                        label="evaluation_completion",
                    )
                except TimeoutError:
                    print(f"  [session {session_idx}] ⏰ timeout waiting for evaluation")
                    result.cycles.append(cycle)
                    break

                eval_wait_s = time.perf_counter() - t_eval
                cycle.steps.append(StepTiming(
                    step="agent_evaluation",
                    latency_s=eval_wait_s,
                ))
                action = snap.get("next_action", "")

            # ── Evaluation ready → fetch it ─────────────
            if snap.get("evaluation_ready"):
                _, timing = await _timed(
                    "fetch_evaluation",
                    client.get(f"/learning/{session_id}/evaluation"),
                )
                cycle.steps.append(timing)

            # ── Advance based on next_action ────────────
            if action == "choose_branch":
                options = snap.get("options", [])
                recommended = snap.get("recommended_node")
                selected = recommended or (options[0] if options else "")
                payload = {"selected_node": selected} if selected else {}
                _, timing = await _timed(
                    "advance_choose_branch",
                    client.post(f"/learning/{session_id}/continue", json=payload),
                )
                cycle.steps.append(timing)

            elif action in ("advance", "advance_remediation"):
                _, timing = await _timed(
                    f"advance_{action}",
                    client.post(f"/learning/{session_id}/continue", json={}),
                )
                cycle.steps.append(timing)

            result.cycles.append(cycle)
            print(
                f"  [session {session_idx}] cycle {cycle_num + 1}: "
                f"'{current}' — {cycle.total_s:.2f}s "
                f"(lesson_gen: {wait_s:.2f}s, eval: {eval_wait_s if 'eval_wait_s' in locals() else 0:.2f}s)"
            )

            if snap.get("status") == "completed" or action == "completed":
                print(f"  [session {session_idx}] 🎓 Curriculum completed!")
                break

    return result


# ── Reporting ─────────────────────────────────────────────────

def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return s[f] + (k - f) * (s[c] - s[f])


def print_report(results: list[SessionResult]) -> dict[str, Any]:
    """Print a human-readable summary and return structured metrics."""
    all_cycles = [c for r in results for c in r.cycles]
    cycle_times = [c.total_s for c in all_cycles]

    # Per-step aggregation
    step_times: dict[str, list[float]] = {}
    for cycle in all_cycles:
        for step in cycle.steps:
            step_times.setdefault(step.step, []).append(step.latency_s)

    print("\n" + "=" * 65)
    print("  COGNIMAP END-TO-END BENCHMARK RESULTS")
    print("=" * 65)

    print(f"\n  Sessions:        {len(results)}")
    print(f"  Total cycles:    {len(all_cycles)}")
    total_wall = sum(r.total_s for r in results)
    print(f"  Total wall time: {total_wall:.1f}s")

    if cycle_times:
        print(f"\n  ── Cycle latency (seconds) ──")
        print(f"     Min:    {min(cycle_times):>8.2f}")
        print(f"     Mean:   {sum(cycle_times)/len(cycle_times):>8.2f}")
        print(f"     Median: {_percentile(cycle_times, 0.5):>8.2f}")
        print(f"     p90:    {_percentile(cycle_times, 0.9):>8.2f}")
        print(f"     p95:    {_percentile(cycle_times, 0.95):>8.2f}")
        print(f"     Max:    {max(cycle_times):>8.2f}")

    if step_times:
        print(f"\n  ── Per-step mean latency ──")
        for step_name, times in sorted(step_times.items()):
            mean = sum(times) / len(times)
            print(f"     {step_name:<28s} {mean:>7.2f}s  (n={len(times)})")

    print("\n" + "=" * 65)

    # Structured output
    metrics: dict[str, Any] = {
        "sessions": len(results),
        "total_cycles": len(all_cycles),
        "total_wall_seconds": round(total_wall, 2),
    }
    if cycle_times:
        metrics["cycle_latency_s"] = {
            "min": round(min(cycle_times), 3),
            "mean": round(sum(cycle_times) / len(cycle_times), 3),
            "median": round(_percentile(cycle_times, 0.5), 3),
            "p90": round(_percentile(cycle_times, 0.9), 3),
            "p95": round(_percentile(cycle_times, 0.95), 3),
            "max": round(max(cycle_times), 3),
        }
    metrics["step_mean_latency_s"] = {
        name: round(sum(t) / len(t), 3)
        for name, t in sorted(step_times.items())
    }
    return metrics


def save_results(metrics: dict[str, Any], output: Path) -> None:
    """Append structured results to the shared results.json."""
    run_data = {
        "test": "e2e_learning_cycle",
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "metrics": metrics,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        try:
            doc = json.loads(output.read_text())
            if isinstance(doc, dict) and isinstance(doc.get("runs"), list):
                doc["runs"].append(run_data)
            else:
                doc = {"schema_version": 1, "runs": [run_data]}
        except (json.JSONDecodeError, ValueError):
            doc = {"schema_version": 1, "runs": [run_data]}
    else:
        doc = {"schema_version": 1, "runs": [run_data]}

    output.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"\n  Results saved to {output}")


# ── CLI ───────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="End-to-end Cognimap learning cycle benchmark.",
    )
    p.add_argument("--base-url", default=DEFAULT_BASE, help="API base URL")
    p.add_argument("--topic", default=DEFAULT_TOPIC, help="Learning topic")
    p.add_argument(
        "--course-mode", default="micro", choices=["micro", "detailed"],
        help="Course mode (micro is faster for benchmarks)",
    )
    p.add_argument("--cycles", type=int, default=2, help="Max cycles per session")
    p.add_argument(
        "--concurrent-sessions", type=int, default=1,
        help="Number of sessions to run in parallel",
    )
    p.add_argument("--output", type=Path, default=RESULTS_FILE, help="Results JSON file")
    return p.parse_args()


async def _main() -> int:
    args = parse_args()
    print(f"\n  Cognimap E2E Benchmark")
    print(f"  Target:      {args.base_url}")
    print(f"  Topic:       {args.topic}")
    print(f"  Course mode: {args.course_mode}")
    print(f"  Cycles:      {args.cycles}")
    print(f"  Concurrent:  {args.concurrent_sessions}\n")

    tasks = [
        run_session(args.base_url, args.topic, args.course_mode, args.cycles, i + 1)
        for i in range(args.concurrent_sessions)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out errors
    good: list[SessionResult] = []
    for r in results:
        if isinstance(r, Exception):
            print(f"  ✗ Session failed: {r}")
        else:
            good.append(r)

    if not good:
        print("\n  All sessions failed. Check worker and API logs.")
        return 1

    metrics = print_report(good)
    save_results(metrics, args.output)
    return 0


def main() -> int:
    return asyncio.run(_main())


if __name__ == "__main__":
    raise SystemExit(main())
