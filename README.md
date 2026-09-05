# Browser Provisioner

Mirrors a real Chromium tab into a web page. The backend drives the tab over
the Chrome DevTools Protocol and replays viewer input, while the data plane
streams JPEG frames through the backend to a `<canvas>`.

Learning project, not a hardened product: no auth, no rate limiting. It's a
reference for the core idea, not something to deploy as is.

### See it in action

Focus view mirrors a single session full-width:

![Focus view: a mirrored Wikipedia tab with tab strip, address bar, and state toolbar](static/image_2.png)

Grid view keeps several leased browsers side by side:

![Grid view: two mirrored browser sessions next to a create-browser tile](static/image.png)

Both screenshots show real Chromium tabs running on the server, not iframes:
full clipboard support (copy/read/write round-tripped through CDP), full tab
support (list/create/activate/close, all in sync with the mirrored session),
and cursor shape. The cursor CDP reports has to be translated into a CSS
cursor and played back in the frontend itself, it's not part of the frame
stream.

## Architecture

Four layers, each with a single job:

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
                                    │      Data Plane      │  │ Postgres │
                                    │  worker per Chromium │  └──────────┘
                                    │  lifecycle · CDP ·   │
                                    │  screencast · state  │
                                    └──────────┬───────────┘
                                               ▼
                                          ┌──────────┐
                                          │ Chromium │
                                          └──────────┘
```

**Frontend** (`frontend/`) — an Angular SPA that only ever talks to the
backend. It opens a session (`POST /api/v1/sessions`) and gets back two
backend-relative paths: one for JSON-RPC, one for frames. The screencast is
drawn frame by frame straight onto a `<canvas>`; there is no iframe and no
embedded browser engine. Every DOM event on the canvas is translated into a
CDP input command and replayed on the real tab.

**Gateway** (`backend/src/backend/browser_tunnel/`) — the session-bound edge
of the backend. It speaks JSON-RPC 2.0 to the frontend, translates it to CDP,
and relays binary screencast frames from a worker, so worker and CDP addresses
never leave the server. Its three layers are separable:
`application/` defines what a browser can do,
`infrastructure/cdp_browser` implements that over CDP, and `presentation/`
exposes it as session-bound JSON-RPC.

**Control Plane** (`backend/src/backend/features/`) — owns the session and
browser lifecycle: `sessions` (open, suspend, resume, capture and mount
state), `leases` (who holds which browser), `browsers` (the pool provisioned
against the workers), and `health`. State documents live in Postgres; the
data-plane gateway moves them between worker and database.

**Data Plane** (`data-plane/`) — one worker process per Chromium. It owns the
browser lifecycle, exposes CDP, screencast frames, browser/authentication
state capture, and video recordings over an internal HTTP API, and reports
health and capacity. Workers are addressed only by the backend, through
`BACKEND_BROWSER_*_DATA_PLANE_URL`.

Two transports carry live traffic: the backend WebSocket carries JSON-RPC
commands plus tab/navigation/cursor state, and a separate data-plane
WebSocket carries the binary JPEG frames.

## Tunneled events

**Navigation:** navigate to URL, back, forward, reload (with optional cache
bypass), stop loading.

**Mouse:** down, move, up, with button, modifier, and click-count tracking
(covers drags and held buttons), plus scroll.

**Keyboard:** key down/up, raw key down, char events, text insertion, and
paste.

**Clipboard:** copy, read, write.

**Tabs:** list, create, activate, close. Every tab command replies with the
full tab list.

**Pushed by the backend:** tab list changes, navigation state (title, URL,
loading, can-go-back/forward, error), cursor style, and target
crashed/detached.

## Setup

```bash
uv sync
(cd frontend && npm install)
uv run pre-commit install
```

## Development

```bash
# Start Postgres, run the migrations, then the backend and data-plane workers
docker compose up --build

# Start the frontend
(cd frontend && npm run dev)

# Then open in a browser: http://localhost:5173

uv run python -m backend.browser_tunnel.schema_export # write JSON Schema and OpenRPC
(cd frontend && npm run generate) # regenerate schemas and both TypeScript clients
./scripts/generate_http_clients.sh # regenerate the Python HTTP clients
# Schema changes: write a migration and apply it (BACKEND_DATABASE_URL points at Postgres)
(cd backend && uv run alembic revision --autogenerate -m "...")
(cd backend && uv run alembic upgrade head)

uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
(cd frontend && npm run build)        # type-check and build the frontend
```

The frontend can also just be started with `npm run dev` from `frontend/` after
`npm install`.
`predev` regenerates the schemas and both clients first. Vite hot-reloads on
HTML/CSS/TS changes and proxies `/api` to the backend on port 8000.

Two generated TypeScript clients live in npm workspace packages:
`frontend/generated` holds the backend browser JSON-RPC client rendered from the
OpenRPC document, and `frontend/generated-backend` holds the backend HTTP
client that [orval](https://orval.dev) renders from
`schemas/backend-openapi.json` (see `frontend/orval.config.ts`).
`npm run check:generated` (from `frontend/`) flags a stale one.

The typed Python client for the data-plane HTTP API is rendered from its
OpenAPI document into the uv workspace package `generated/`, so the
infrastructure layer imports `generated.data_plane` instead of hand-writing
requests.
`./scripts/generate_http_clients.sh --check` flags a stale client.

## Session state

Authentication and browser UI state are separate documents:

- `authentication_state` contains cookies and origin-localStorage and can be
  reused as a browser profile.
- `browser_state` contains tabs, the active-tab index, scroll positions and
  per-tab sessionStorage.

`POST /api/v1/sessions` accepts either or both documents. Authentication is
mounted before browser state, so restored tabs navigate with the supplied
login. A running session also exposes each document independently at
`/api/v1/sessions/{id}/authentication-state` and
`/api/v1/sessions/{id}/browser-state` via `GET` and `PUT`. Suspend/resume keeps
both documents, but stores them separately.

## Backend protocol

The session-bound backend WebSocket uses JSON-RPC 2.0:

- `ws://127.0.0.1:8000/api/v1/sessions/{session_id}/tunnel`
- JSON Schema: `/api/v1/browser/schema.json`
- OpenRPC: `/api/v1/browser/openrpc.json`

The data plane exposes JPEG frames as binary messages on
`/api/v1/browser/{browser_id}/screencast`.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "browser.nav.navigate",
  "params": { "url": "https://example.com" }
}
```

Server-pushed events arrive as `browser.event`; `params.type` tells frames
apart from tab/navigation state and crashed/detached targets. Frames are
JPEG, base64-encoded for the JSON transport.

The backend derives internal CDP URLs from `BACKEND_BROWSER_*_DATA_PLANE_URL`
and configures its view through `BACKEND_BROWSER_WIDTH` and
`BACKEND_BROWSER_HEIGHT`. Chromium
lifecycle settings such as `DATA_PLANE_EXECUTABLE`, `DATA_PLANE_HEADLESS`,
`DATA_PLANE_CAPACITY`, and `DATA_PLANE_STARTUP_TIMEOUT` belong to the
data-plane worker.

Smoke test against a real browser:
`uv run python backend/tests/browser_tunnel/manual_smoke.py`.
