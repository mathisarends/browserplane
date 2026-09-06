# Planes and responsibilities

## The split

```text
CONTROL PLANE                          DATA PLANE
decides                                executes
─────────────────────────────          ─────────────────────────────
Who holds browser #1?                  Which Chromium PID is running?
Until when?                            Which CDP socket is open?
Which generation is current?           Which profile dir is on disk?
May this session still act?            Which files were downloaded?

truth: a Postgres row                  truth: a live process
recoverable after a crash              thrown away after a crash
```

The two answers must never be derived from each other. A `READY` row does not
prove a clean Chromium; a live Chromium does not entitle anybody to use it.
Bringing them back together is exactly what the reclaim path does — see
[Browser lifecycle](browser-lifecycle.md).

## Who answers what

| Question | Owner |
| --- | --- |
| Is this browser free? | Postgres row, locked `FOR UPDATE SKIP LOCKED` |
| Whose lease is it, and until when? | `leases` table (`expires_at`, `reclaim_after`) |
| Is this holder still the current one? | `generation` — checked in DB *and* on the worker |
| Does the session survive a page reload? | `sessions` table, independent of any socket |
| What is in the browser right now? | The worker, over CDP |
| Is the runtime actually clean? | The worker, after `POST /api/v1/release` |

## Processes

```text
API process              Scheduler                 Browser worker
───────────────          ─────────────────         ────────────────────
HTTP + WebSocket         request dispatcher        one Chromium per worker
JSON-RPC → CDP relay     lease reaper              CDP, screencast, downloads
lease keeper per tunnel  slot reconciliation       state capture / mount
local waiter registry    recovery scans            release + re-provision
notification listener
```

- **API process** is edge-only. It serves requests, keeps a lease alive while a
  control tunnel is open, and parks callers that are waiting for capacity. It
  owns no background business work.
- **Scheduler** owns everything periodic: assigning queued requests, reclaiming
  expired leases, reconciling slots against reality. Several may run; Postgres
  row locks, not leader election, keep them from colliding.
- **Browser worker** owns one Chromium and every resource around it. It has no
  database and no object-storage credentials.

**Today** the API process still does the scheduler's job: `lifespan.py` calls
`BrowserService.start()`, runs a reaper task, and reaps once at boot. That makes
API startup provision browsers nobody asked for, and gives every replica its own
copy of the same background work.

**Planned:** a separate scheduler entry point using the same image and DI
container; the API lifespan then opens only edge infrastructure.

## Rules at the boundary

1. **No external call inside a DB transaction.** Row locks are held for
   microseconds; worker HTTP and CDP happen after the commit.
2. **The database decides, the worker enforces.** Every lifecycle call to a
   worker carries `(browser_id, generation)`; a stale generation is refused
   there, not just in Postgres.
3. **A lease is never handed on by resetting a status.** The runtime is
   destroyed and rebuilt first — a status update cannot un-log-in a browser.
4. **Notifications are hints.** They may be lost, doubled, or coalesced; after
   every wakeup the state is re-read from Postgres.
5. **Nothing is released because a socket dropped.** Deadlines release things.
