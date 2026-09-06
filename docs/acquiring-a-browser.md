# Acquiring a browser

Implemented in `backend/src/backend/features/browser_requests/`; the concept is
`REQUEST_CONCEPT.md`. `POST /api/v1/sessions` no longer fails when the pool is
full — it waits until its deadline.

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

Runs in the scheduler process, woken by notification and otherwise every five
seconds:

1. expire everything past its deadline
2. resume an orphaned reservation first — a row that still carries a
   `browser_id` is a leader that died mid-provisioning
3. otherwise claim the oldest `QUEUED` request (FIFO by `created_at, id`) plus a
   free slot, both `FOR UPDATE SKIP LOCKED`
4. provision outside the transaction: release, start, mount state
5. persist lease, session, and `ASSIGNED` in one transaction
6. notify, so the waiting API process wakes up

One dispatcher is active at a time (`pg_try_advisory_lock`), but that is not
what prevents double assignment — row locks and the re-checks in step 5 are.
Losing the lock cancels local work; committed reservations are recovered by the
next leader through step 2.

## Notifications

A thin infrastructure port, deliberately not a domain event bus:

```text
Notifier.notify(channel, payload)   →  pg_notify, inside the committing transaction
Listener                            →  one long-lived LISTEN connection, reconnects
```

Domain and application code never see `asyncpg`, `LISTEN`, or a channel name.
The message means only: *the persistent state may have changed*. A waiter also
re-reads on its own every five seconds, so a lost notification costs latency,
never progress.

## Caller-facing behaviour

```text
request id supplied again   same input  → the same wait is picked back up
                            other input → 409, the id belongs to something else
deadline passed             → 408, request EXPIRED
cancelled                   → 409
HTTP client disconnects     → 499, the request is cancelled
GET    /api/v1/browser-requests/{id}?owner_id=…   inspect a wait
DELETE /api/v1/browser-requests/{id}?owner_id=…   cancel a wait
```

Resume takes the same path: `resume_session_id` makes the assignment reuse the
suspended session's id and its checkpoint, so a resumed session waits for
capacity exactly like a new one.
