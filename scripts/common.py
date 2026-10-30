"""Shared helpers for the standalone API performance scripts."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import platform
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_FILE = SCRIPT_DIR / "results.json"
DEFAULT_URL = "http://127.0.0.1:8002/health"


def positive_int(value: str) -> int:
    """argparse converter for integer values greater than zero."""
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def non_negative_int(value: str) -> int:
    """argparse converter for integer values of zero or greater."""
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return result


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--url",
        default=os.environ.get("COGNIMAP_TEST_URL", DEFAULT_URL),
        help=(
            "GET target URL (default: %(default)s; may also be set with "
            "COGNIMAP_TEST_URL)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="per-request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        metavar="NAME: VALUE",
        help="optional HTTP header; repeat to add more headers",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_FILE,
        help="JSON history file (default: %(default)s)",
    )


def validate_url_and_timeout(url: str, timeout: float) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("--url must be a complete http:// or https:// URL")
    if timeout <= 0:
        raise ValueError("--timeout must be greater than zero")


def parse_headers(values: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for item in values:
        name, separator, value = item.partition(":")
        if not separator or not name.strip() or "\r" in value or "\n" in value:
            raise ValueError(f"invalid header {item!r}; expected NAME: VALUE")
        headers[name.strip()] = value.strip()
    return headers


def safe_target(url: str) -> str:
    """Return the URL without credentials, query values, or fragments."""
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parsed.port
    except ValueError:
        port = None
    authority = f"{host}:{port}" if port is not None else host
    return urlunsplit((parsed.scheme, authority, parsed.path or "/", "", ""))


async def get_once(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = await client.get(url)
        return {
            "latency_seconds": time.perf_counter() - started,
            "status_code": response.status_code,
            "bytes_received": len(response.content),
            "success": 200 <= response.status_code < 300,
            "error_type": None,
        }
    except Exception as exc:  # Keep measuring other requests after a network error.
        return {
            "latency_seconds": time.perf_counter() - started,
            "status_code": None,
            "bytes_received": 0,
            "success": False,
            "error_type": type(exc).__name__,
        }


async def warm_up(
    client: httpx.AsyncClient, url: str, count: int
) -> list[dict[str, Any]]:
    results = []
    for _ in range(count):
        results.append(await get_once(client, url))
    return results


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def summarize(
    results: list[dict[str, Any]],
    elapsed_seconds: float,
    *,
    configured_concurrency: int,
    observed_max_in_flight: int,
) -> dict[str, Any]:
    latencies = sorted(result["latency_seconds"] for result in results)
    status_counts = Counter(
        str(result["status_code"])
        for result in results
        if result["status_code"] is not None
    )
    error_counts = Counter(
        result["error_type"] for result in results if result["error_type"]
    )
    successes = sum(1 for result in results if result["success"])
    total = len(results)
    latency_ms = {
        "min": min(latencies, default=0.0) * 1000,
        "mean": (sum(latencies) / total * 1000) if total else 0.0,
        "p50": _percentile(latencies, 50) * 1000,
        "p90": _percentile(latencies, 90) * 1000,
        "p95": _percentile(latencies, 95) * 1000,
        "p99": _percentile(latencies, 99) * 1000,
        "max": max(latencies, default=0.0) * 1000,
    }
    return {
        "request_count": total,
        "successful_requests": successes,
        "failed_requests": total - successes,
        "success_rate_percent": (successes / total * 100) if total else 0.0,
        "elapsed_seconds": elapsed_seconds,
        "requests_per_second": total / elapsed_seconds if elapsed_seconds else 0.0,
        "latency_ms": latency_ms,
        "status_codes": dict(sorted(status_counts.items())),
        "transport_errors": dict(sorted(error_counts.items())),
        "bytes_received": sum(result["bytes_received"] for result in results),
        "configured_concurrency": configured_concurrency,
        "observed_max_in_flight": observed_max_in_flight,
    }


def environment_info() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
    }


def make_run(test_name: str, url: str, settings: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "test": test_name,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "target": safe_target(url),
        "settings": settings,
        "environment": environment_info(),
        "metrics": metrics,
    }


def record_result(output_path: Path, run: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        try:
            document = json.loads(output_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict) or not isinstance(document.get("runs"), list):
                raise ValueError("expected an object containing a runs array")
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"cannot append to invalid results file {output_path}: {exc}") from exc
    else:
        document = {"schema_version": 1, "runs": []}
    document["runs"].append(run)

    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=output_path.parent, delete=False
        ) as temp_file:
            temp_name = temp_file.name
            json.dump(document, temp_file, indent=2)
            temp_file.write("\n")
        Path(temp_name).replace(output_path)
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)


def print_run(run: dict[str, Any], output_path: Path) -> None:
    print(json.dumps(run, indent=2))
    print(f"\nResults appended to: {output_path}")
