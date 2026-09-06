# Browserplane

Mirrors a real Chromium tab into a web page. The backend drives the tab over the
Chrome DevTools Protocol and replays viewer input; the browser worker streams
JPEG frames through the backend to a `<canvas>`.

Learning project: no auth, no rate limiting.

- [See it in action](#see-it-in-action)
- [Architecture](#architecture)
- [Deep dives](#deep-dives)
- [Setup](#setup)
- [Development](#development)
- [Protocol](#protocol)
- [Configuration](#configuration)

## See it in action

A leased session — tab strip, address bar, and state toolbar:

![A mirrored Wikipedia tab with tab strip, address bar, and state toolbar](static/image_2.png)

The gallery — several leased browsers side by side:

![Two mirrored browser sessions next to a create-browser tile](static/image.png)

Real Chromium tabs on the server, not iframes: clipboard round-tripped through
CDP, tabs in sync with the mirrored session, and cursor shape translated from
CDP into a CSS cursor in the frontend (it is not part of the frame stream).

## Architecture

```text
┌─────────────┐   HTTP + WS (JSON-RPC)   ┌───────────────────────────────┐
│  Frontend   │ ───────────────────────▶ │  Backend · API                │
│ Angular SPA │ ◀─────────────────────── │  gateway (JSON-RPC ⇄ CDP)     │
│  <canvas>   │   JPEG frames, events    │  sessions · requests · leases │
└─────────────┘                          └──────┬─────────────────┬──────┘
                                                │ SQL             │ CDP · WS
┌─────────────────────────────┐                 ▼                 │
│  Scheduler                  │        ┌───────────────────┐      │
│  request dispatcher         │──SQL──▶│     Postgres      │      │
│  lease reaper               │        │  source of truth  │      │
│  slot reconciliation        │        │  slots · leases   │      │
│  leader-elected             │        │  sessions · state │      │
└──────┬──────────────────────┘        └───────────────────┘      │
       │ internal HTTP: start · release · state                   │
       ▼                                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Browser worker × 2 — one Chromium each                              │
│  lifecycle · CDP · screencast · downloads · recordings · state       │
└───────────────────────────────┬──────────────────────────────────────┘
                                ▼
                          ┌──────────┐
                          │ Chromium │
                          └──────────┘
```

| Component | Path | Owns |
| --- | --- | --- |
| Frontend | `frontend/` | `<canvas>`; replays DOM events as CDP commands, talks only to the backend |
| Gateway | `backend/…/features/browser_tunnel/` | JSON-RPC 2.0 ⇄ CDP, frame relay; keeps worker and CDP addresses off the wire |
| API | `backend/…/features/` | sessions, browser requests, leases, browsers, recordings, health |
| Scheduler | `backend/src/backend/scheduler.py` | dispatches queued requests, reaps leases, reconciles slots |
| Browser worker | `browser_worker/` | one Chromium each: lifecycle, CDP, screencast, downloads, recordings, state |

**Control plane / data plane.** The control plane decides who may use which
browser until when — its truth is a Postgres row, and it survives a crash. The
data plane *is* the browser — its truth is a running process, and it is thrown
away. A `READY` row does not prove a clean Chromium, and a live Chromium
entitles nobody to use it: only a proven cleanup plus a fresh runtime returns a
slot to the pool. Leases end on deadlines, never on a dropped socket.

Live traffic uses two transports: the backend WebSocket for JSON-RPC and
tab/navigation/cursor state, a browser worker WebSocket for binary JPEG frames.

## Deep dives

| Document | Question it answers |
| --- | --- |
| [docs/planes.md](docs/planes.md) | Who owns which truth, and which process may do what |
| [docs/browser-lifecycle.md](docs/browser-lifecycle.md) | Slot vs. runtime vs. lease, and how fencing keeps them honest |
| [docs/acquiring-a-browser.md](docs/acquiring-a-browser.md) | What happens when the pool is full and a caller waits |
| [docs/session-state.md](docs/session-state.md) | Why authentication and browser state are two documents |

Working specs: `LEASE_CONCEPT.md`, `REQUEST_CONCEPT.md`.

## Setup

```bash
uv sync
(cd frontend && npm install)
uv run pre-commit install
```

## Development

```bash
# Postgres, MinIO, migrations, backend, scheduler and browser workers
docker compose up --build

# Frontend on http://localhost:5173
(cd frontend && npm run dev)

uv run python -m backend.features.browser_tunnel.schema_export # JSON Schema and OpenRPC
(cd frontend && npm run generate) # schemas and both TypeScript clients
./scripts/generate_http_clients.sh # Python HTTP clients
(cd backend && uv run alembic revision --autogenerate -m "...")
(cd backend && uv run alembic upgrade head)

uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
(cd frontend && npm run build) # type-check and build
```

Keep awaited application or repository calls separate from response mapping so
both steps remain easy to read:

```python
request = await repository.get(request_id)
return BrowserRequestResponse.model_validate(request)
```

Generated clients: `frontend/generated` (browser JSON-RPC, from OpenRPC),
`frontend/generated-backend` (backend HTTP, via [orval](https://orval.dev) from
`schemas/backend-openapi.json`), and the uv workspace package `generated/`
(typed Python client for the browser worker API). `npm run check:generated` and
`./scripts/generate_http_clients.sh --check` flag a stale one. `predev`
regenerates schemas and clients; Vite hot-reloads and proxies `/api` to 8000.

Smoke test: `uv run python backend/tests/browser_tunnel/manual_smoke.py`.

## Protocol

```text
POST    /api/v1/sessions                        open a session; waits for capacity
GET     /api/v1/browser-requests/{id}           inspect or pick a wait back up
DELETE  /api/v1/browser-requests/{id}           cancel a wait
POST    /api/v1/sessions/{id}/lease/renew       heartbeat without a tunnel
GET|PUT /api/v1/sessions/{id}/browser-state     · /authentication-state
ws      /api/v1/sessions/{id}/tunnel            JSON-RPC 2.0
ws      /api/v1/browser/{browser_id}/screencast worker frames
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "browser.nav.navigate",
  "params": { "url": "https://example.com" }
}
```

| Group | Methods |
| --- | --- |
| Navigation | navigate, back, forward, reload (optional cache bypass), stop |
| Mouse | down, move, up — button, modifier, click-count tracking — and scroll |
| Keyboard | key down/up, raw key down, char, text insertion, paste |
| Clipboard | copy, read, write |
| Tabs | list, create, activate, close; every reply carries the full tab list |
| Pushed | tab list, navigation state, cursor style, target crashed/detached |

Server-pushed events arrive as `browser.event`; `params.type` tells frames apart
from tab/navigation state and crashed/detached targets.

Session state is two independent documents — `authentication_state` (cookies and
origin-localStorage; a reusable, encrypted profile) and `browser_state` (tabs,
active tab, scroll, sessionStorage; a checkpoint). Authentication is mounted
first, so restored tabs navigate logged in. See
[docs/session-state.md](docs/session-state.md).

## Configuration

```text
BACKEND_BROWSER_WIDTH / _HEIGHT              the mirrored viewport
BACKEND_LEASE_*                              heartbeat 10s, TTL 30s, grace 45s
BACKEND_BROWSER_WORKER_{1,2}_URL             internal worker addresses only
BACKEND_AUTHENTICATION_STATE_ENCRYPTION_KEY  scripts/generate_fernet_key.sh
BROWSER_WORKER_EXECUTABLE / _HEADLESS / _CAPACITY / _STARTUP_TIMEOUT
```

Completed recordings are streamed from the worker into the `recordings/` prefix
of the S3-compatible `browser-recordings` bucket. MinIO serves S3 on
`http://localhost:9000` and its console on `http://localhost:9001`; credentials
default to `minioadmin` / `minioadmin` and are overridden with
`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_RECORDINGS_BUCKET`.
