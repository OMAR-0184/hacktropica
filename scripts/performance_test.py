"""Measure sequential GET latency and throughput for a Cognimap API endpoint."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

import httpx

if __package__:
    from .common import (
        add_common_arguments,
        get_once,
        make_run,
        non_negative_int,
        parse_headers,
        positive_int,
        print_run,
        record_result,
        summarize,
        validate_url_and_timeout,
        warm_up,
    )
else:
    from common import (
        add_common_arguments,
        get_once,
        make_run,
        non_negative_int,
        parse_headers,
        positive_int,
        print_run,
        record_result,
        summarize,
        validate_url_and_timeout,
        warm_up,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a sequential API performance check and save its metrics."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--iterations",
        type=positive_int,
        default=50,
        help="measured requests to send (default: %(default)s)",
    )
    parser.add_argument(
        "--warmup",
        type=non_negative_int,
        default=5,
        help="sequential warm-up requests excluded from metrics (default: %(default)s)",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> tuple[dict, bool]:
    validate_url_and_timeout(args.url, args.timeout)
    headers = parse_headers(args.header)
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        warmup_results = await warm_up(client, args.url, args.warmup)
        results = []
        started = time.perf_counter()
        for _ in range(args.iterations):
            results.append(await get_once(client, args.url))
        elapsed = time.perf_counter() - started

    metrics = summarize(
        results,
        elapsed,
        configured_concurrency=1,
        observed_max_in_flight=1,
    )
    metrics["warmup_requests"] = len(warmup_results)
    metrics["warmup_failures"] = sum(not item["success"] for item in warmup_results)
    run_data = make_run(
        "sequential_performance",
        args.url,
        {
            "iterations": args.iterations,
            "warmup": args.warmup,
            "timeout_seconds": args.timeout,
        },
        metrics,
    )
    record_result(args.output, run_data)
    return run_data, metrics["failed_requests"] == 0


def main() -> int:
    args = parse_args()
    try:
        run_data, passed = asyncio.run(run(args))
    except (ValueError, httpx.InvalidURL) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    print_run(run_data, args.output)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
