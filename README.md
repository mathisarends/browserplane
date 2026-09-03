# BrowserTunnel

Mirrors a real Chromium tab into a web page. The backend drives the tab over
the Chrome DevTools Protocol, streams its frames to a `<canvas>`, and replays
the viewer's input back onto it. No video codec, just JSON-RPC over a
WebSocket.

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

```
┌──────────────────────┐   single WebSocket, JSON-RPC 2.0    ┌───────────────────────────┐
│       Frontend        │ ──────────────────────────────────▶ │       BrowserTunnel       │
│  (TypeScript, Vite)   │  requests: navigate, mouse, key...  │  BrowserSession             │
│                        │ ◀────────────────────────────────  │  Browser (nav · input ·    │
│  <canvas> viewport     │  frames, tab/nav/cursor state       │  clipboard · tabs)         │
└────────────────────────┘                                    └─────────────┬──────────────┘
                                                                              │
                                                                    internal raw CDP
                                                                              │
                                                                    ┌─────────▼─────────┐
                                                                    │ Data-plane worker  │
                                                                    │ owns Chromium      │
                                                                    └────────────────────┘
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
- One socket, both directions running at once: requests go one way, a
  notification stream (frames, tab/nav/cursor state) goes the other.

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

**Pushed to the client:** screencast frames, tab list changes, navigation
state (title, URL, loading, can-go-back/forward, error), cursor style, and
target crashed/detached.

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

## Backend protocol

One WebSocket, JSON-RPC 2.0:

- `ws://127.0.0.1:8000/api/v1/browser/ws`
- JSON Schema: `/api/v1/browser/schema.json`
- OpenRPC: `/api/v1/browser/openrpc.json`

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
