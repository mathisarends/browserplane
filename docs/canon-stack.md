# Canon stack

The backend and worker use `fastapi-canon==0.8.1`; browser RPC uses
`fastapi-rpckit==0.4.1`. The frontend uses the reviewed Lit Canon revision
`4fe0827b03bacc3f04008b8300b3e6942593c323`. See [the vendored package record](../vendor/README.md).

## Composition and ownership

Each backend capability is an explicit Canon feature. The composition roots own
Dishka and its lifespan; features own their providers and routers. Browser and
repository ABCs and their records live in framework-free domain packages;
infrastructure implements those owned interfaces. Application services coordinate
domain work, and presentation maps it into HTTP or RPC responses.

HTTP routes keep Canon's typed error contracts and generated OpenAPI responses.
The static error-contract checker runs in strict mode: proven missing declarations
fail the check. It also reports incomplete analysis of dynamic adapters and
external calls. A zero-gap result does not mean every possible exception was
proved; incomplete operations remain visible in the check output.

## Browser RPC

Free functions on `RpcChannel` declare the browser methods; `RpcService` owns the
socket endpoint and the OpenRPC contract. The backend selects a browser from the
leased session and supplies it through the connection context. Missing tabs have
a declared typed RPC error. Read-only tab and clipboard operations are explicitly
idempotent; writes are never marked retryable.

The official generated client supplies typed calls, events, heartbeat handling,
bounded reconnect attempts and middleware. One FIFO middleware orders all input
commands, including mouse, keyboard and clipboard commands. The server dispatches
one command at a time, preserving that order through CDP. A new session generation
invalidates old HTTP/socket completions; cancellation withdraws a queued request
and closes resources acquired after the UI stopped waiting.

## Lit composition and HTTP queries

`createApp`, `defineFeature` and a lazy `definePage` compose the workspace. Context
providers own identity, view state, persistence and admin services. Each browser
panel provides its own session. Native Lit signals drive rendering; subscriptions,
DOM listeners, sockets and frame painters are released with their owner.

There is one context-provided TanStack `QueryClient`. Lit Canon API generates the
HTTP functions, query options, mutation options, query keys and problem guards.
`configureApiFetch` configures the common transport once. Commands use generated
HTTP functions; cached reads use generated query options. No component invents
cache keys or duplicates response/status parsing.

The owner-session query factory is shared by the route's `prefetchQueries` and
the layout's `createQueryController`. Both use the same key and freshness window,
so route prefetch seeds the component's cache. Creating or closing a session and
capturing saved state invalidate the relevant generated keys. Query state and
local UI signals have separate owners.

The existing JSON-RPC and screencast protocols remain in use. Canon's separate
Streams and WebRTC packages are unnecessary for these transports.

## Pins and generated sources

Direct external Python and npm dependencies, including the wheel build backend,
have exact versions. Commit `uv.lock` and `frontend/package-lock.json` after any
dependency change. Lit Canon archives have source revisions and SHA-256 records;
npm verifies archive integrity. The Orval version inside Lit Canon API stays
pinned because the generator depends on its AST. Compatible patches for its
transitive `undici`, `fast-uri` and `source-map-js` dependencies are pinned with
root npm overrides. Docker bases and external Compose images use immutable digests.

The generated OpenRPC document is committed so a fresh checkout can check its
contract and client before regeneration. OpenAPI documents are exported during
the HTTP client checks.

Regenerate through `npm --prefix frontend run generate`. Never edit
`frontend/generated/src`, `frontend/generated-backend/src/canon`, or
`generated/src/generated/browser_worker` by hand. `check:generated` checks the RPC,
Lit Canon HTTP and Python worker clients against their source contracts.

## Verification

```console
uv sync --locked
npm ci --ignore-scripts --prefix frontend
uv run --locked python scripts/check.py all
uv run --locked python scripts/check.py browser
docker build -f backend/Dockerfile -t browserplane-backend:check .
docker build -f browser_worker/Dockerfile -t browserplane-worker:check .
```

`check.py` also accepts `lint`, `test`, `contracts`, and `build`. Tests run once per
workspace member in separate processes, avoiding colliding `tests` package names.
The browser check needs Docker and Chrome or Playwright Chromium. The worker
integration tests also need FFmpeg on `PATH`; CI installs both native tools before
running the suite. On Linux, run
`npx playwright install --with-deps chromium` from `frontend`, then set
`BROWSER_EXECUTABLE` to `require('playwright').chromium.executablePath()` from Node.

The browser smoke starts isolated Postgres and MinIO containers, applies migrations,
and starts a real worker, backend, scheduler and Vite frontend. It exercises
provisioning, rendered screencast frames, ordered typing, clipboard copy/paste,
tabs, a saved checkpoint, Focus mode and the admin overview. It removes its own
processes, containers and network afterward. It does not use the Compose volumes.
CI repeats the locked installs, checks, real browser smoke and both image builds.
