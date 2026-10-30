# API performance scripts

These scripts send read-only `GET` requests. By default, they measure the API's
`/health` endpoint at `http://127.0.0.1:8002/health`. Start the API and its
Postgres/Redis services before running them.

```sh
python3 scripts/performance_test.py
python3 scripts/concurrency_test.py
```

The scripts use `httpx`, which is included in the project's dependencies. Install
them first with `python3 -m pip install -r requirements.txt` if needed.

The sequential check reports latency percentiles and request throughput. The
concurrency check reports the same metrics while keeping the number of in-flight
requests within `--concurrency` (default: 10). Both exclude warm-up requests from
the main measurements and append each run to `scripts/results.json`.

Use `--url` or `COGNIMAP_TEST_URL` to target another HTTP(S) GET endpoint. The
performance script accepts `--iterations`; the concurrency script accepts
`--requests` and `--concurrency`. Both accept `--warmup`, `--timeout`, repeated
`--header 'NAME: VALUE'`, and `--output`. Query strings and supplied headers are
not written to the result file. Keep request counts and concurrency modest when
targeting a shared or production service.
