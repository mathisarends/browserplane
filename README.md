# Browserplane

Mirrors a real Chromium tab into a web page. The backend drives the tab over
the Chrome DevTools Protocol and replays viewer input; the browser worker streams
JPEG frames through the backend to a `<canvas>`.

Learning project: no auth, no rate limiting.

### See it in action

A leased session — tab strip, address bar, and state toolbar:

![A mirrored Wikipedia tab with tab strip, address bar, and state toolbar](static/image_2.png)

The gallery — several leased browsers side by side:

![Two mirrored browser sessions next to a create-browser tile](static/image.png)

Real Chromium tabs on the server, not iframes: clipboard round-tripped through
CDP, tabs in sync with the mirrored session, and cursor shape translated from
CDP into a CSS cursor in the frontend (it is not part of the frame stream).

## Architecture

```text
┌───────────────┐   HTTP + WS (JSON-RPC)   ┌──────────────────────────────┐
│   Frontend    │ ───────────────────────▶ │           Backend            │
│  Angular SPA  │ ◀─────────────────────── │                              │
│  <canvas>     │   JPEG frames, events    │  ┌────────────────────────┐  │
└───────────────┘                          │  │  Gateway               │  │
                                           │  │  browser_tunnel        │  │
                                           │  │  JSON-RPC + WS relay   │  │
                                           │  └───────────┬────────────┘  │
                                           │  ┌───────────┴────────────┐  │
                                           │  │  Control Plane         │  │
                                           │  │  sessions · leases ·   │  │
                                           │  │  browsers · state      │  │
                                           │  └───────────┬────────────┘  │
                                           └──────────────┼───────────────┘
                                     internal HTTP/CDP/WS │        │ SQL
                                                          ▼        ▼
                                    ┌──────────────────────┐  ┌──────────┐
                                    │      Browser Worker      │  │ Postgres │
                                    │  worker per Chromium │  └──────────┘
                                    │  lifecycle · CDP ·   │
                                    │  screencast · state  │
                                    └──────────┬───────────┘
                                               ▼
                                          ┌──────────┐
                                          │ Chromium │
                                          └──────────┘
```

**Frontend** (`frontend/`) — Angular SPA, talks only to the backend. Opens a
session (`POST /api/v1/sessions`), gets back two backend-relative paths, draws
frames onto a `<canvas>` and replays every DOM event as a CDP input command.

**Gateway** (`backend/src/backend/features/browser_tunnel/`) — session-bound edge.
Speaks JSON-RPC 2.0, translates to CDP, relays frames, keeps worker and CDP
addresses off the wire. `application/` defines what a browser can do,
`infrastructure/cdp_browser` implements it over CDP, `presentation/` exposes
it.

**Control Plane** (`backend/src/backend/features/`) — `sessions`, `leases`,
`browsers`, `recordings`, `health`. Owns the session and browser lifecycle;
state documents live in Postgres, and completed recording files are persisted
to object storage by the backend.

**Browser Worker** (`browser_worker/`) — one worker per Chromium: lifecycle, CDP,
screencast, state capture, recording capture, health and capacity. It streams
the completed recording video to the backend and has no object-storage
credentials. Reachable only via `BACKEND_BROWSER_*_BROWSER_WORKER_URL`.

Live traffic uses two transports: the backend WebSocket for JSON-RPC and
tab/navigation/cursor state, a browser worker WebSocket for binary JPEG frames.

### Control plane and data plane

The line through the whole system: the **control plane** decides who may use
which browser until when — its truth is a Postgres row, and it survives a crash.
The **data plane** *is* the browser — its truth is a running process, and it is
thrown away. Neither derives the other's answer.

- A `READY` row does not prove a clean Chromium, and a live Chromium entitles
  nobody to use it. Only a proven cleanup plus a fresh runtime makes a slot
  `READY` again — an expiring lease never does.
- A **lease** is a renewable, time-boxed claim on one browser slot: heartbeat
  10 s, TTL 30 s, then 45 s of grace in which the same holder can come back.
  After that the reclaim is irreversible.
- The **generation** is the fence. It rides along on every worker lifecycle
  call, and the hard reclaim replaces the Chromium process — so a stale holder
  is dead, not merely unauthorized.
- Nothing is released because a socket dropped; deadlines release things. A
  reloaded tab reattaches, a hung stream cannot pin a browser.

Details and diagrams: [`docs/`](docs/README.md).

## Tunneled events

**Navigation:** navigate, back, forward, reload (optional cache bypass), stop.

**Mouse:** down, move, up — with button, modifier and click-count tracking —
plus scroll.

**Keyboard:** key down/up, raw key down, char, text insertion, paste.

**Clipboard:** copy, read, write.

**Tabs:** list, create, activate, close. Every command replies with the full
tab list.

**Pushed by the backend:** tab list, navigation state (title, URL, loading,
can-go-back/forward, error), cursor style, target crashed/detached.

## Setup

```bash
uv sync
(cd frontend && npm install)
uv run pre-commit install
```

## Development

```bash
# Postgres, MinIO, migrations, backend and browser workers
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

After the backend stops a recording, it streams each completed segment from the
browser worker into the `recordings/` prefix of the S3-compatible
`browser-recordings` bucket. MinIO exposes its S3 API at
`http://localhost:9000` and its object browser/admin console at
`http://localhost:9001`. Development credentials default to
`minioadmin` / `minioadmin`; override them and the bucket name with
`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, and `MINIO_RECORDINGS_BUCKET`.

`predev` regenerates schemas and clients; Vite hot-reloads and proxies `/api`
to port 8000.

Generated clients: `frontend/generated` (browser JSON-RPC, from OpenRPC),
`frontend/generated-backend` (backend HTTP, via [orval](https://orval.dev)
from `schemas/backend-openapi.json`), and the uv workspace package
`generated/` (typed Python client for the browser worker API). `npm run
check:generated` and `./scripts/generate_http_clients.sh --check` flag a stale
one.

## Session state

Two independent documents — *who you are* and *where you were*:

- `authentication_state` — cookies and origin-localStorage, reusable as a named
  browser profile, encrypted at rest.
- `browser_state` — tabs, active-tab index, scroll positions, per-tab
  sessionStorage, captured as a checkpoint.

Splitting them is what lets one login start fifty fresh browsers, and lets a
restored set of tabs land on a different identity. `POST /api/v1/sessions`
accepts either or both; authentication is mounted first, so restored tabs
navigate logged in instead of bouncing off a login screen. Suspend captures both
and hands the browser back; resume mounts them onto whichever slot is free, so
the session id is stable while the browser underneath is not. See
[`docs/session-state.md`](docs/session-state.md). A running session exposes each at
`/api/v1/sessions/{id}/authentication-state` and
`/api/v1/sessions/{id}/browser-state` (`GET`/`PUT`). Suspend/resume keeps both,
stored separately.

## Backend protocol

- `ws://127.0.0.1:8000/api/v1/sessions/{session_id}/tunnel` — JSON-RPC 2.0
- Browser worker frames: `/api/v1/browser/{browser_id}/screencast`

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "browser.nav.navigate",
  "params": { "url": "https://example.com" }
}
```

Server-pushed events arrive as `browser.event`; `params.type` tells frames
apart from tab/navigation state and crashed/detached targets.

The view is configured through `BACKEND_BROWSER_WIDTH` and
`BACKEND_BROWSER_HEIGHT`; Chromium lifecycle settings (`BROWSER_WORKER_EXECUTABLE`,
`BROWSER_WORKER_HEADLESS`, `BROWSER_WORKER_CAPACITY`, `BROWSER_WORKER_STARTUP_TIMEOUT`)
belong to the worker.

Smoke test: `uv run python backend/tests/browser_tunnel/manual_smoke.py`.
