# Cognimap API Docs (Client Integration Guide)

Last updated: April 5, 2026

This document is written for frontend/client developers integrating with the Cognimap backend.

## 1. API Overview

Cognimap exposes:

- Auth APIs (`/auth/*`)
- Learning session APIs (`/learning/*`)
- Workflow orchestration APIs (`next-action`, `continue`, `workflow`)
- Resource search API (`/learning/search`)
- Real-time updates over WebSocket (`/learning/{session_id}/stream`)

Base API URL:

- `http://<your-host>:<port>`

Built-in docs:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

Health check:

- `GET /`

## 2. Auth and Headers

All `/learning/*` routes require Bearer auth.

Header format:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Token source:

- `POST /auth/login/json` (recommended for SPAs)
- `POST /auth/login` (form-data, mainly Swagger/OAuth tooling)

WebSocket auth is different:

- Token is passed as query param: `?token=<jwt>`

### 2.1 Rate Limits and Resource Quotas

To ensure platform stability, the API enforces the following limits:

- **Rate Limits:** Write operations (POST, PATCH, DELETE) are limited to **30 requests per minute** per user (sliding window).
- **Session Cap:** Each user is limited to a maximum of **5 active (non-archived) learning sessions** at any given time. If a user tries to start a 6th session, the API will return a `403 Forbidden` error. They must archive an existing session first.

## 3. Core Runtime Concepts

### 3.1 Session lifecycle

`status` values from `GET /learning/{session_id}/status`:

- `initializing`
- `running`
- `ready`
- `evaluating`
- `completed`
- `error`
- `archived`

### 3.2 Graph waiting states

`waiting_on` (from `next-action`, `choices`, `workflow`) can include:

- `evaluator` -> client must submit quiz answers
- `next` -> client can choose next branch
- `bridge` -> remediation advance path

### 3.3 Journey modes

- `learn`: normal forward learning flow
- `review`: revisiting/repairing previously seen nodes

### 3.4 Traversal modes

- `dfs`
- `bfs`

Set at session start, and can be overridden later via `continue`/`next` request payload.

### 3.5 Dynamic LLM Orchestrator (New)
The agent now uses a dynamic LLM-driven orchestrator node that evaluates the user's `mastery`, `weak_areas`, and `history` at every step to decide the next action. Instead of a rigid linear sequence (`tutor -> quiz -> evaluate`), the orchestrator can:
- Skip quizzes if mastery is already high.
- Drop immediately into a remediation `bridge` topic if historical data suggests a deep dive is needed.
- Repeatedly test the user via `quiz` if they failed recently.

**Frontend Impact:** You must **not** assume the next state. Always rely on the `action` field in `JourneyNextActionResponse` (or `/workflow`) to know what to render next. The orchestrator exposes its internal thought process via `orchestrator_reasoning` in the graph state, which can be useful for debugging or showing a "What the tutor is thinking" UI.

## 4. Recommended Client Orchestration

Use these endpoints as your primary loop:

1. `POST /learning/start`
2. Poll `GET /learning/{session_id}/workflow` until `status = ready`
3. Read `next_action` and branch:

- `take_quiz`: load quiz (`GET /quiz`), submit via `POST /continue` with `answers`
- `choose_branch`: submit `POST /continue` with optional `selected_node`
- `advance` / `advance_remediation`: `POST /continue` with empty body
- `wait`: keep polling
- `completed`: show completion UI

Why `workflow` first?

- It is the most consolidated endpoint and remains safe even early in initialization.
- It includes readiness flags (`lesson_ready`, `quiz_ready`, `evaluation_ready`) plus node graph metadata.

## 5. Quick End-to-End Sequence

1. Register: `POST /auth/register`
2. Login: `POST /auth/login/json`
3. Start: `POST /learning/start`
4. Poll: `GET /learning/{session_id}/workflow`
5. Read lesson: `GET /learning/{session_id}/lesson`
6. Read quiz: `GET /learning/{session_id}/quiz`
7. Submit answers: `POST /learning/{session_id}/continue`
8. Read evaluation: `GET /learning/{session_id}/evaluation`
9. Continue branching: `POST /learning/{session_id}/continue`

## 6. Endpoint Reference

## 6.1 Health

### `GET /`

Response `200`:

```json
{
  "status": "ok",
  "message": "Cognimap Engine is running."
}
```

## 6.2 Auth

### `POST /auth/register`

Creates a user.

Request:

```json
{
  "email": "learner@example.com",
  "password": "StrongPassword123!",
  "username": "learner_one"
}
```

Notes:

- `username` is optional.
- If omitted, backend auto-generates a unique username from email.
- Username format: lowercase letters, numbers, underscores.
- Username length: 3..32.

Success `200` (`UserResponse`):

```json
{
  "id": 1,
  "email": "learner@example.com",
  "username": "learner_one",
  "created_at": "2026-04-05T07:15:00"
}
```

Common errors:

- `400` email already registered
- `409` username already taken
- `422` invalid username format/length

### `POST /auth/login/json`

Recommended login route for browser/mobile clients.

Request:

```json
{
  "email": "learner@example.com",
  "password": "StrongPassword123!"
}
```

Success `200`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Errors:

- `401` incorrect email/password

### `POST /auth/login`

Same auth behavior as `/auth/login/json`, but uses form fields:

- `username` (email)
- `password`

### `GET /auth/profile`

Returns current user.

### `PATCH /auth/profile`

Updates username.

Request:

```json
{
  "username": "new_name"
}
```

Errors:

- `409` username already taken
- `422` invalid username

### `GET /auth/me` (deprecated)

Deprecated alias of `/auth/profile`.

Response headers include deprecation hints:

- `Deprecation: true`
- `Link: </auth/profile>; rel="successor-version"`

## 6.3 Learning Sessions

### `GET /learning/sessions`

Lists non-archived sessions for the authenticated user.

Query params:

- `limit` (1..100, default 20)
- `offset` (>= 0, default 0)

Response:

```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "topic": "DSA",
      "status": "ready",
      "created_at": "2026-04-05T07:20:00",
      "overall_progress": 0.0
    }
  ],
  "total": 1
}
```

### `POST /learning/start`

Creates a new session and enqueues async graph startup.

Request:

```json
{
  "topic": "DSA",
  "course_mode": "detailed",
  "traversal_mode": "dfs"
}
```

Request fields:

- `topic` (required)
- `course_mode` (`detailed` or `micro`)
- `traversal_mode` (`dfs` or `bfs`)

Success `200`:

```json
{
  "session_id": "aeb7e326-0d3c-4f02-b6a2-648063b25c03",
  "message": "Learning session started asynchronously. Connect to websocket for streaming."
}
```

Validation errors (`422`) return structured details for invalid topic:

```json
{
  "detail": {
    "code": "EMPTY_TOPIC",
    "message": "Topic cannot be empty.",
    "suggestions": ["Python fundamentals", "Data structures"]
  }
}
```

Operational errors:

- `403 Forbidden` if the user has reached the maximum active session limit (5 sessions).
- `503 Service Unavailable` if background queue is unavailable
- `429 Too Many Requests` if the user exceeds the 30 req/min rate limit.

### `GET /learning/{session_id}/status`

Returns high-level DB session status.

Response:

```json
{
  "session_id": "uuid",
  "status": "initializing",
  "current_phase": "root",
  "topic": "Organic Chemistry",
  "error_message": null
}
```

### `DELETE /learning/{session_id}`

Soft-archives a session.

Response:

```json
{
  "status": "archived",
  "session_id": "uuid"
}
```

## 6.4 Lesson, Quiz, Evaluation

### `GET /learning/{session_id}/lesson`

Fetch lesson content for active node, or a specific node via query param:

- `node_id` (optional)

Use case for `node_id`:

- show lesson content from history for previously generated nodes

Response (`LessonResponse`):

```json
{
  "session_id": "uuid",
  "node_id": "Intro to DSA",
  "tutor_content": {
    "learning_objective": "...",
    "explanation": "...",
    "examples": ["..."],
    "common_misconception": "...",
    "practice_task": "...",
    "code_snippet": null
  },
  "curator_content": {
    "articles": [{"title": "...", "url": "https://...", "description": "..."}],
    "videos": [],
    "courses": [],
    "references": []
  },
  "is_remediation": false,
  "parent_node_id": null,
  "depth": 0,
  "node_kind": "intro",
  "path_from_root": ["Intro to DSA"],
  "is_math_heavy": false,
  "is_expanded": true
}
```

Key errors:

- `409` if session not in readable state (`initializing`, `running`, `evaluating`, `error`, `archived`)
- `404` if `node_id` is not part of this session
- `409` with code `LESSON_NOT_GENERATED` if node exists but lesson was not generated yet

`LESSON_NOT_GENERATED` example:

```json
{
  "detail": {
    "code": "LESSON_NOT_GENERATED",
    "message": "Lesson content for node 'X' is not generated yet.",
    "hint": "Select this node as your next branch and continue learning to generate it."
  }
}
```

### `GET /learning/{session_id}/quiz`

Returns the quiz for the current node.

Response:

```json
{
  "session_id": "uuid",
  "node_id": "Intro to DSA",
  "questions": [
    {
      "question_id": "q1",
      "question": "What is ...?",
      "options": ["A", "B", "C", "D"]
    }
  ],
  "question_count": 5,
  "numerical_target_ratio": 0.0,
  "actual_numerical_ratio": 0.6
}
```

Error:

- `409` if session status is not `ready`

### `GET /learning/{session_id}/evaluation`
### `GET /learning/{session_id}/evaluation/result`

Both return latest evaluation payload.

Response (`EvaluationResult`):

```json
{
  "score": 0.8,
  "weak_areas": ["Recursion"],
  "feedback": "Solid work...",
  "passed": true,
  "next_action": "next_topic",
  "question_results": [
    {
      "question_id": "q1",
      "question": "...",
      "options": ["..."],
      "correct_index": 1,
      "user_index": 1,
      "is_correct": true
    }
  ],
  "question_count": 5,
  "numerical_target_ratio": 0.3,
  "actual_numerical_ratio": 0.2
}
```

If evaluation is not available yet:

- `409` with detail: `Evaluation result is not available yet. Submit quiz answers first.`

### `POST /learning/{session_id}/evaluate` (deprecated)

Use `POST /learning/{session_id}/continue` with `answers` instead.

## 6.5 Orchestration and Branching

### `GET /learning/{session_id}/next-action`

Lightweight CTA endpoint for UI step decisions.

Common `action` values:

- `wait`
- `take_quiz`
- `choose_branch`
- `advance`
- `advance_remediation`
- `completed`
- `blocked`

Important behavior:

- During quiz stage (`action = take_quiz`), response can include:
  - `options`
  - `recommended_node`
  - `recommendation_reason`
  - `recommendation_factors`
- That means UI can preselect next node before submitting quiz answers.

### `POST /learning/{session_id}/continue`

Primary endpoint for progression.

Request body (`ContinueRequest`, all optional):

```json
{
  "answers": [0, 2, 1, 3, 0],
  "selected_node": "Common Sorting Algorithms",
  "traversal_mode": "dfs",
  "client_request_id": "req-123"
}
```

Usage patterns:

- Quiz submit only: send `answers`
- Branch selection only: send `selected_node`
- Quiz + branch preselection together: send `answers` and `selected_node`
- Advance with recommendation: send empty body `{}`

Typical responses (`ContinueResponse`):

1) Needs quiz answers:

```json
{
  "session_id": "uuid",
  "status": "needs_input",
  "action": "take_quiz",
  "message": "Quiz answers are required to continue.",
  "required_input": "answers",
  "enqueued": false,
  "options": ["Node A", "Node B"],
  "recommended_node": "Node B",
  "request_status": "accepted",
  "request_id": "req-123"
}
```

2) Accepted and processing evaluation:

```json
{
  "session_id": "uuid",
  "status": "processing",
  "action": "submit_evaluation",
  "message": "Answers accepted. Evaluation is processing.",
  "enqueued": true,
  "request_status": "accepted",
  "request_id": "req-123"
}
```

3) Accepted and advancing:

```json
{
  "session_id": "uuid",
  "status": "processing",
  "action": "advance",
  "message": "Advancing to the next step.",
  "enqueued": true,
  "options": ["Node A", "Node B"],
  "recommended_node": "Node B",
  "request_status": "accepted",
  "request_id": "req-123"
}
```

4) Session not ready:

```json
{
  "session_id": "uuid",
  "status": "waiting",
  "action": "wait",
  "message": "Session is 'running'. Wait until it becomes 'ready'.",
  "enqueued": false,
  "request_status": "accepted"
}
```

Validation and conflict behavior:

- Invalid branch node -> `422` with code `INVALID_SELECTED_NODE`
- Wrong stage for selected node (for remediation path) -> `needs_input` response
- In-flight concurrent progression -> `request_status = in_progress`

Idempotency notes:

- `client_request_id` support is active when backend journey orchestrator v2 is enabled for that session.
- Reusing same `client_request_id` with different payload returns `422`.
- Reusing same `client_request_id` with same payload returns cached response and `request_status = duplicate`.

### `GET /learning/{session_id}/choices`

Returns branch options, recommendation, and metadata.

Useful when you want a dedicated branch-picker screen.

### `POST /learning/{session_id}/next` (deprecated)

Deprecated compatibility endpoint.

Use `POST /learning/{session_id}/continue`.

## 6.6 Session Insight Endpoints

### `GET /learning/{session_id}/progress`

Returns:

- subtopic statuses
- scores/attempts
- history
- traversal metadata
- node hierarchy snapshots

### `GET /learning/{session_id}/workflow`

Best single endpoint for orchestration UIs.

Includes:

- `status`, `current_phase`, `topic`, `current_node`
- `waiting_on`, `next_action`
- `options`, recommendations
- readiness booleans (`lesson_ready`, `quiz_ready`, `evaluation_ready`)
- graph hierarchy (`active_frontier`, `current_path`, `children_map`, `node_catalog`)

Important behavior:

- If graph snapshot is not initialized yet, endpoint still returns a safe payload (instead of 400) with DB status and defaults.

## 6.7 Search

### `GET /learning/search`

Query params:

- `q` required, length 2..200
- `type` one of `articles | videos | courses | all` (default `all`)
- `max_results` integer 1..10 (applies to single-category modes)

Response:

```json
{
  "query": "binary trees",
  "type": "all",
  "results": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "...",
      "category": "articles"
    }
  ]
}
```

Implementation note:

- `type = all` runs category searches concurrently and merges categories.

## 6.8 WebSocket

### `WS /learning/{session_id}/stream?token=<jwt>`

Auth failures:

- missing token -> close `4001`, reason `Missing authentication token`
- invalid token -> close `4001`, reason `Invalid token`

Realtime payloads are JSON strings published from worker/engine, commonly:

```json
{"type":"status","message":"Graph Initialized"}
```

```json
{"type":"node_update","node":"quiz","data":{}}
```

```json
{"type":"error","message":"..."}
```

Channel mapping:

- Redis pub/sub channel: `session:{session_id}`

## 7. Primary Response Models (Client-facing)

### 7.1 `JourneyNextActionResponse`

Key fields:

- `action`, `status`, `message`
- `waiting_on`
- `required_input`
- `options`, `recommended_node`, `recommendation_reason`, `recommendation_factors`
- `can_go_back`, `previous_node`
- hierarchy metadata: `parent_node_id`, `depth`, `node_kind`, `path_from_root`, `is_math_heavy`, `is_expanded`, `option_metadata`

### 7.2 `ContinueResponse`

Same orchestration fields plus:

- `enqueued`
- `request_status`: `accepted | duplicate | in_progress`
- `request_id`

### 7.3 `WorkflowSnapshotResponse`

High-level fields for dashboard/state rendering:

- lifecycle: `status`, `current_phase`
- actioning: `next_action`, `waiting_on`, `options`, recommendation fields
- readiness: `lesson_ready`, `quiz_ready`, `evaluation_ready`
- graph: `active_frontier`, `current_path`, `children_map`, `node_catalog`

## 8. Error Handling Guide

Common HTTP status patterns:

- `401 Unauthorized`
  - missing/invalid bearer token
- `403 Forbidden`
  - session cap reached (max 5 active sessions per user)
- `404 Not Found`
  - session not owned by user / not found
  - node not in session
- `409 Conflict`
  - endpoint called at wrong stage (`ready` required, eval not ready, lesson unavailable stage)
- `422 Unprocessable Content`
  - validation failures (topic, answers, selected node)
  - idempotency key reused with different payload (v2)
- `429 Too Many Requests`
  - sliding window rate limit exceeded (30 writes/min)
- `503 Service Unavailable`
  - queue unavailable during `start` / `continue` / `next`

Current error envelope (standardized):

```json
{
  "error": {
    "code": "HTTP_ERROR",
    "message": "selected_node is not in available options.",
    "status": 422
  }
}
```

Common error codes:

- `HTTP_ERROR` (mapped from explicit HTTPException)
- `VALIDATION_ERROR` (request body/query validation failures)
- `DATABASE_ERROR` (DB connectivity/driver failures)
- `CACHE_ERROR` (Redis failures)
- `INTERNAL_SERVER_ERROR` (unexpected uncaught server errors)

Compatibility note:

- Older deployments may still return legacy `{"detail": ...}` payloads.
- Production clients should parse both `error.message` and fallback `detail`.

## 9. Frontend Integration Patterns

## 9.1 Shared fetch helper (TypeScript)

```ts
export async function apiFetch<T>(
  path: string,
  token: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers || {}),
    },
  });

  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    throw { status: res.status, body };
  }

  return res.json() as Promise<T>;
}
```

## 9.2 Suggested orchestration loop

```ts
type NextAction =
  | "wait"
  | "take_quiz"
  | "choose_branch"
  | "advance"
  | "advance_remediation"
  | "completed"
  | "blocked";

async function runLoop(sessionId: string, token: string) {
  while (true) {
    const wf = await apiFetch<any>(`/learning/${sessionId}/workflow`, token);

    if (wf.status === "completed" || wf.next_action === "completed") break;

    switch (wf.next_action as NextAction) {
      case "wait":
      default:
        await new Promise((r) => setTimeout(r, 1500));
        break;

      case "take_quiz": {
        const quiz = await apiFetch<any>(`/learning/${sessionId}/quiz`, token);
        const answers = collectAnswersFromUI(quiz.questions);
        const selected_node = getOptionalBranchSelectionFromUI(wf.options);

        await apiFetch(`/learning/${sessionId}/continue`, token, {
          method: "POST",
          body: JSON.stringify({ answers, selected_node }),
        });
        break;
      }

      case "choose_branch": {
        const selected_node = chooseBranch(wf.options, wf.recommended_node);
        await apiFetch(`/learning/${sessionId}/continue`, token, {
          method: "POST",
          body: JSON.stringify({ selected_node }),
        });
        break;
      }

      case "advance":
      case "advance_remediation":
        await apiFetch(`/learning/${sessionId}/continue`, token, {
          method: "POST",
          body: JSON.stringify({}),
        });
        break;
    }
  }
}
```

## 9.3 WebSocket hookup

```ts
function connectSessionStream(apiBaseHttp: string, sessionId: string, token: string) {
  const wsBase = apiBaseHttp.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/learning/${sessionId}/stream?token=${encodeURIComponent(token)}`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("session event", data);
    } catch {
      console.log("raw session event", event.data);
    }
  };

  return ws;
}
```

## 10. Deprecated Routes Summary

Deprecated but still present:

- `GET /auth/me` -> use `GET /auth/profile`
- `POST /learning/{session_id}/evaluate` -> use `POST /learning/{session_id}/continue` with `answers`
- `POST /learning/{session_id}/next` -> use `POST /learning/{session_id}/continue`

Deprecation headers are set where applicable (`Deprecation`, `Link`).

## 11. Production Notes for Client Teams

- Do not hardcode `localhost` in production API/WS URLs.
- Parse standardized `error.message` first, then fallback to legacy `detail`.
- Prefer `workflow` for rendering orchestration state.
- Keep UI resilient to transient `wait` states.
- Use retries/backoff for polling loops.
- Keep token refresh/login UX in place for `401` recovery.

## 12. Railway Deployment Runbook (Backend)

Use this when deploying API + Postgres + Redis on Railway.

### 12.1 Topology

Create/verify 3 services in the same Railway project:

- API service (from this GitHub repo)
- Postgres service
- Redis service

### 12.2 Start command

Set API service start command:

```bash
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Do not use `docker-compose` commands in Railway service start.

### 12.3 Required production env vars (API service)

Set these in API service Variables:

- `COGNIMAP_ENVIRONMENT=production`
- `COGNIMAP_SECRET_KEY=<long-random-secret>`
- `COGNIMAP_CORS_ORIGINS=https://<your-frontend-domain>`
- `COGNIMAP_REDIS_URL=${{Redis.REDIS_URL}}`

Set DB URLs explicitly (async + sync):

```bash
COGNIMAP_DATABASE_URL=postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
COGNIMAP_DATABASE_URL_SYNC=postgresql://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
```

Why both?

- Async runtime uses `COGNIMAP_DATABASE_URL`.
- Sync migration/runtime tools may use `COGNIMAP_DATABASE_URL_SYNC`.

### 12.4 Runtime validation behavior

In production, app startup fails fast if any of these are true:

- default `COGNIMAP_SECRET_KEY`
- `COGNIMAP_CORS_ORIGINS` contains `*`
- DB/Redis URLs point to localhost

If startup fails, check deploy logs for:

- `Invalid production configuration: ...`

### 12.5 Smoke test checklist after deploy

1. `GET /` returns `{"status":"ok"...}`.
2. `GET /docs` is reachable.
3. Register/login works (`/auth/register`, `/auth/login/json`).
4. `POST /learning/start` returns `session_id`.
5. Poll `/learning/{session_id}/status` until `ready` or `error`.
6. `GET /learning/{session_id}/workflow` returns `next_action`.
7. Submit quiz answers through `/learning/{session_id}/continue`.

### 12.6 Troubleshooting quick map

`SyntaxError ... unterminated triple-quoted string`

- A Python file has invalid syntax; fix and redeploy.
- This error prevents route import, making API look partially missing.

`OSError ... Connect call failed ('127.0.0.1', 5435)`

- API is still using localhost DB URL in production.
- Set `COGNIMAP_DATABASE_URL` and `COGNIMAP_DATABASE_URL_SYNC` to Railway Postgres host vars.

Session stuck:

```json
{"status":"initializing","current_phase":"root"}
```

- Check worker/queue connectivity (Redis URL).
- Check API deploy logs for queue enqueue failures.
- Confirm Postgres connectivity and tables/migrations.

`WebSocket close 4003 (Session access denied)`

- JWT user does not own that `session_id`.
- Ensure frontend uses current user's token for that session.
