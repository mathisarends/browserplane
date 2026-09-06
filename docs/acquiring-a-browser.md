# Acquiring a browser

Status: **planned** — the concept is `REQUEST_CONCEPT.md`, the draft lives in
`backend/src/backend/features/browser_requests/`. Today `POST /api/v1/sessions`
fails immediately with `NO_BROWSER_AVAILABLE` when the pool is full.

## The goal

```python
lease = await control_plane.acquire_browser(owner_id=owner_id, timeout=60)
```

One `await`. No polling loop in the caller, no retry ladder. Waiting parks a
coroutine; it occupies no thread, and — this is the part that constrains the
design — it must occupy no database connection either.

## Flow

```text
        persist the request            (QUEUED, deadline, owner)
                 │
                 ▼
        try an immediate atomic grant
                 │
         ┌───────┴────────┐
         │                │
      possible       not possible
         │                │
         ▼                ▼
     ASSIGNED          QUEUED
         │                │
         │                ▼
         │        register a local future
         │                │
         │          await wakeup ◀──── notification · timeout · slow rescan
         │                │
         └───────▶ re-read the state from Postgres
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          ASSIGNED    terminal    keep waiting
       read the lease  raise       loop again
```

The future carries **no payload** — only "something may have changed". The lease
is always read back from the database. That is what makes a lost, duplicated, or
coalesced notification harmless.

## Request states

```text
QUEUED ──▶ PROVISIONING ──▶ ASSIGNED     (terminal, carries lease_id)
   │                                     
   ├──────────────────────▶ CANCELLED    (terminal, caller gave up)
   └──────────────────────▶ EXPIRED      (terminal, deadline passed)
```

The request ends where the lease begins: after `ASSIGNED`, everything is the
lease's business ([Browser lifecycle](browser-lifecycle.md)).

## Why the request is persistent

```text
API process dies    ─▶ its futures vanish, the row does not; another
                       process picks the request up by id
scheduler dies      ─▶ its successor continues QUEUED and PROVISIONING
notification lost   ─▶ the slow rescan finds the work anyway
caller cancels      ─▶ recorded first; a grant that raced it stays
                       discoverable and expires under lease policy
```

An in-memory queue would lose every one of those.

## Database boundary

The request-scoped `AsyncSession` commits at the end of an HTTP request. A wait
can last minutes, so it cannot borrow that session. Waiting is a sequence of
short, independent transactions:

```text
enqueue ──┐          ┌── claim request + browser
          ├─ wait ───┤
read ─────┘          └── write lease, set ASSIGNED
```

Between them, session, transaction, and pooled connection are all released. Ten
thousand waiting callers cost ten thousand futures, not ten thousand
connections.

## Dispatcher

Woken by notification, plus a slow recovery scan:

1. claim the oldest valid `QUEUED` request (FIFO by `created_at, id`)
2. reserve a free slot exclusively
3. provision the runtime if needed — outside the transaction
4. persist lease and `ASSIGNED` atomically
5. notify, so the waiting API process wakes up

Doubled assignment is prevented by row locks, compare-and-set updates, and
database constraints — not by the dispatcher being alone.

## Notifications

A thin infrastructure port, deliberately not a domain event bus:

```text
Notifier.notify(channel, payload)   →  pg_notify, inside the committing transaction
Listener                            →  one long-lived LISTEN connection, reconnects
```

Domain and application code never see `asyncpg`, `LISTEN`, or a channel name.
The message means only: *the persistent state may have changed*.
