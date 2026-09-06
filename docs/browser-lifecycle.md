# Browser lifecycle

## Four things that are easy to confuse

```text
SLOT        stable id + worker url            never changes
            00000000-…-0001 → browser-worker-1

RUNTIME     the Chromium process, profile,    disposable
            CDP sockets, downloads, workspace

LEASE       one owner's exclusive claim       time-boxed
            on one slot                       id == session id

GENERATION  counter per slot, bumped every    the fence
            time a runtime is replaced
```

A slot is what the pool schedules. A runtime is what gets destroyed. A lease is
what expires. A generation is what makes an old holder harmless.

## Browser states

```text
STARTING ──▶ READY ──▶ LEASED ──▶ RECYCLING ──▶ READY
                │         │           │
                └─────────┴───────────┴──▶ FAILED ──▶ (retry)
```

`READY` is a strong promise: no live lease, and a freshly verified runtime.
Only a proven cleanup produces it — a lease expiring never does.

## Lease states and timing

Defaults: heartbeat **10 s**, TTL **30 s**, grace **45 s**, reaper every **5 s**.

```text
last successful renew
0s              10s             20s             30s                    75s
├───────────────┼───────────────┼───────────────┼──────────────────────┤
        ACTIVE — may act        │       GRACE — must renew first       │
                                │  slot still reserved for this lease  │
                                expires_at                  reclaim_after
                                                                       │
                                                     RECLAIMING — no way back
```

```text
              renew
           ┌────────┐
           │        ▼
        ACTIVE ──────────▶ RECLAIMING ──────────▶ RELEASED
           │                    ▲                     
   close · suspend · crash      │  retry with backoff 
           └────────────────────┴──── FAILED
```

`GRACE` is derived, not stored: `state = ACTIVE` and
`expires_at <= now < reclaim_after`. Only the step into `RECLAIMING` is written
down, and it is the point of no return: after it, no renew can revive the lease.

## Allocation

```text
one short transaction              then, outside any transaction
─────────────────────              ─────────────────────────────
lock a READY browser               clear downloads
  FOR UPDATE SKIP LOCKED           mount authentication state
mark it LEASED                     mount browser state
write the lease + deadlines        verify CDP readiness
commit                             hand the session back
```

If any step after the commit fails, the same lease goes to `RECLAIMING` and the
normal cleanup path takes over. The slot is never freed by a plain status write.

## Reclaim

Reaper batches are picked with `FOR UPDATE SKIP LOCKED`, so several schedulers
can run without stepping on each other.

```text
due lease ──▶ CAS to RECLAIMING ──▶ POST /api/v1/release   (worker)
                browser RECYCLING       recordings, downloads, screencast,
                                        Chromium process, workspace
                                             │
                                             ▼
                                    start a new runtime, generation + 1
                                             │
                    ┌────────────────────────┴────────────────────────┐
                    ▼                                                 ▼
        lease RELEASED, browser READY                    lease FAILED, browser
                                                         FAILED, retry later
```

Every step is idempotent. "No browser running" and "directory does not exist"
count as success, so a scheduler that dies mid-cleanup is simply resumed.

## Fencing

Two different problems, two different mechanisms:

| Risk | Guard |
| --- | --- |
| Someone else renews or closes your lease | holder credential *(planned)* |
| A legitimate but *old* holder keeps acting | `generation` |

An already-open CDP socket cannot be checked per command, so the hard fence is
physical: the worker drops the runtime from its registry, kills the process, and
starts a new one. The old socket is dead, not merely unauthorized.

The worker refuses a `create` or `release` whose `(browser_id, generation)` does
not match what it is running — so a stale scheduler cannot release a runtime
that already belongs to the next holder.

## What keeps a lease alive

```text
control tunnel open ──▶ lease keeper renews every 10s   ← the canonical signal
POST /sessions/{id}/lease/renew                         ← for callers without a tunnel
screencast traffic                                      ── does NOT renew
mouse, keyboard, CDP traffic                            ── does NOT renew
tunnel disconnect                                       ── does NOT release
```

Liveness is something a holder states explicitly, not something a busy data
stream implies. That is why a reloaded browser tab can pick its session back up
inside the grace period, and why a hung stream cannot pin a browser forever.
