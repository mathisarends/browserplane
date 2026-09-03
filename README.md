# BrowserTunnel

Mirrors a real Chromium tab into a web page. BrowserTunnel drives the tab over
the Chrome DevTools Protocol and replays viewer input, while the data plane
streams JPEG frames over a separate binary WebSocket to a `<canvas>`.

Learning project, not a hardened product: no auth, no rate limiting. It's a
reference for the core idea, not something to deploy as is.

### See it in action

<video src="https://github.com/user-attachments/assets/b5fd9da7-6170-4d91-a70f-c37da632d414" controls></video>

*Sped up 1.5x.*

As seen in the video: full clipboard support (copy/read/write round-tripped
through CDP), full tab support (list/create/activate/close, all in sync with
the mirrored session), and cursor shape. The cursor CDP reports has to be
translated into a CSS cursor and played back in the frontend itself, it's
not part of the video stream.

## Architecture

```text
Frontend ── JSON-RPC commands/state ──▶ BrowserTunnel ── raw CDP ──▶ Data Plane
    │                                                                      │
    └──────────── binary JPEG screencast WebSocket ◀───────────────────────┘
```

- The tab's screencast comes in frame by frame and gets drawn straight onto
  the canvas. No iframe, no embedded browser engine.
- The tab only exists on the server. Every DOM event the viewer triggers on
  the canvas is translated into a CDP input command and replayed on the real
  tab, so it looks like a real user interacting with it.
- `browsertunnel/src/browsertunnel/application` defines what a browser can do,
  `browsertunnel/src/browsertunnel/infrastructure/cdp_browser` implements that over CDP,
  `browsertunnel/src/browsertunnel/presentation` exposes it as JSON-RPC.
  Each layer can be swapped without touching the others.
- BrowserTunnel carries JSON-RPC commands and tab/navigation/cursor state. A
  separate data-plane WebSocket carries binary JPEG screencast frames.

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

**Pushed by BrowserTunnel:** tab list changes, navigation state (title, URL,
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
# Start the backend (sets up dependencies and .env on demand)
sh scripts/start-backend.sh

# Start the frontend
(cd frontend && npm run dev)

# Then open in a browser: http://localhost:5173

uv run python -m browsertunnel.schema_export # write JSON Schema and OpenRPC into schemas/
(cd frontend && npm run generate:rpc) # regenerate schemas and the TypeScript RPC client
uv run python scripts/generate_http_clients.py # regenerate the Python HTTP clients
uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
(cd frontend && npm run build)        # type-check and build the frontend
```

The frontend can also just be started with `npm run dev` from `frontend/` after
`npm install`.
`predev` regenerates schemas and the RPC client first. Vite hot-reloads on
HTML/CSS/TS changes and proxies `/api` to the backend on port 8000. The
generated client lives in the workspace package `frontend/generated`;
`npm run check:generated` (from `frontend/`) flags a stale one.

The typed Python clients for the control-plane and data-plane HTTP APIs are
rendered from their OpenAPI documents into the uv workspace package
`generated/`, so the infrastructure layer imports
`generated.data_plane` instead of hand-writing requests.
`uv run python scripts/generate_http_clients.py --check` flags a stale client.

## Backend protocol

The BrowserTunnel WebSocket uses JSON-RPC 2.0:

- `ws://127.0.0.1:8000/api/v1/browser/ws`
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

BrowserTunnel requires `BROWSER_CDP_URL` and configures its view through
`BROWSER_WIDTH`, `BROWSER_HEIGHT`, and `BROWSER_SCREENCAST_QUALITY`. Chromium
lifecycle settings such as `DATA_PLANE_EXECUTABLE`, `DATA_PLANE_HEADLESS`,
`DATA_PLANE_CAPACITY`, and `DATA_PLANE_STARTUP_TIMEOUT` belong to the
data-plane worker.

Smoke test against a real browser:
`uv run python browsertunnel/tests/manual_smoke.py`.
