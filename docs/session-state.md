# Session state

A session's state is stored as **two independent documents**. This is the single
design decision that makes "continue where I left off" work without also meaning
"log in again".

```text
authentication state              browser state
────────────────────              ─────────────────────────────
cookies                           tabs and their urls
origin localStorage               active tab index
                                  scroll positions
                                  per-tab sessionStorage

who you are                       where you were
changes rarely                    changes constantly
reusable across sessions          belongs to one moment
encrypted at rest (Fernet)        stored as JSONB
→ AuthenticationProfile           → BrowserCheckpoint
```

## Why not one document

| | one blob | two documents |
| --- | --- | --- |
| Log in once, start 50 runs | copies the login *and* somebody's tabs | one profile, 50 fresh browsers |
| Restore tabs on a fresh login | impossible to separate | mount profile, then checkpoint |
| Rotate a password | rewrite every snapshot | update one profile |
| Secrets at rest | everything gets encrypted, or nothing does | only credentials are encrypted |

They also have different lifetimes. A profile is a named, long-lived identity
that outlives every session that used it. A checkpoint is a moment, taken when a
session is suspended or explicitly checkpointed. A checkpoint may *point at* a
profile, so restoring one implies the other.

## Mount order matters

```text
1. clear downloads        a recycled slot must not leak the last tenant's files
2. mount authentication   cookies and localStorage before anything navigates
3. mount browser state    tabs now load already logged in
```

Reversed, every restored tab would render its logged-out page first, and some
would redirect to a login screen before the cookies ever arrived.

## Suspend and resume

Suspending is not pausing — it captures the session and gives the browser back.

```text
SUSPEND                                   RESUME
──────────────────────────────            ──────────────────────────────
capture authentication ─┐                 read checkpoint
capture browser state ──┤                 read its profile
                        ▼                        │
       save profile + checkpoint                 ▼
                        │                 lease ANY free slot
       session → SUSPENDED                       │
                        │                 clear downloads
       release the lease                  mount authentication
                        │                 mount browser state
       browser is recycled                       │
                                          session → ACTIVE, same session id
```

The session id is stable across suspend/resume; the browser underneath is not.
Resume takes whichever slot is free, on whichever worker — the session was never
attached to hardware, only to two documents.

```text
session lifetime   ├── ACTIVE ──┤          ├── ACTIVE ──┤        ├─ CLOSED
browser lease      ├── lease A ─┤          ├── lease B ─┤
                                └ SUSPENDED ┘
                                 no browser held, TTL 24h by default
```

## Where the state lives

```text
capture / mount    backend ──HTTP──▶ worker ──CDP──▶ Chromium
persistence        Postgres: authentication_profiles (encrypted bytes)
                             browser_checkpoints     (JSONB)
```

The worker only reads and writes what the browser holds — it stores nothing.
Capture and mount are therefore repeatable, and a running session can be
re-pointed at a different profile at any time.

## API surface

```text
POST /api/v1/sessions                    accepts a profile id, a checkpoint id, or both
GET|PUT  /sessions/{id}/browser-state    read or replace tabs and scroll now
PUT      /sessions/{id}/authentication-profile   mount an identity into a live session
POST     /sessions/{id}/authentication-profiles  capture the current identity as a profile
POST     /sessions/{id}/browser-checkpoints      capture the current moment
POST     /sessions/{id}/suspend | /resume        park and pick up again
```
