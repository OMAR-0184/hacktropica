"""Measure endpoint latency and throughput under bounded concurrent GET load."""

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
        description="Run a bounded-concurrency API check and save its metrics."
    )
    add_common_arguments(parser)
    parser.add_argument(
        "--requests",
        type=positive_int,
        default=100,
        help="total measured requests (default: %(default)s)",
    )
    parser.add_argument(
        "--concurrency",
        type=positive_int,
        default=10,
        help="maximum requests in flight (default: %(default)s)",
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
    semaphore = asyncio.Semaphore(args.concurrency)
    in_flight = 0
    observed_max_in_flight = 0

    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        limits=httpx.Limits(
            max_connections=args.concurrency,
            max_keepalive_connections=args.concurrency,
        ),
    ) as client:
        warmup_results = await warm_up(client, args.url, args.warmup)

        async def measured_request() -> dict:
            nonlocal in_flight, observed_max_in_flight
            async with semaphore:
                in_flight += 1
                observed_max_in_flight = max(observed_max_in_flight, in_flight)
                try:
                    return await get_once(client, args.url)
                finally:
                    in_flight -= 1

        started = time.perf_counter()
        results = await asyncio.gather(
            *(measured_request() for _ in range(args.requests))
        )
        elapsed = time.perf_counter() - started

    metrics = summarize(
        results,
        elapsed,
        configured_concurrency=args.concurrency,
        observed_max_in_flight=observed_max_in_flight,
    )
    metrics["warmup_requests"] = len(warmup_results)
    metrics["warmup_failures"] = sum(not item["success"] for item in warmup_results)
    run_data = make_run(
        "concurrency",
        args.url,
        {
            "requests": args.requests,
            "concurrency": args.concurrency,
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
