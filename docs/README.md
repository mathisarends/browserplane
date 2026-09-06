# Architecture

Browserplane hands a caller a real Chromium tab for a while, then takes it back
and proves the next caller gets a clean one. Everything else follows from that.

The system is split along one line: the **control plane** decides *who may use
which browser until when*, the **data plane** *is* the browser. The control
plane's truth lives in Postgres; the data plane's truth is a running process.
Neither may guess the other's answer.

```text
       ┌─────────────────────────────────────────────────────────┐
 HTTP  │  API process                              control plane │
 + WS ─▶  sessions · tunnel · screencast relay · waiting callers │
       └────────────────────────────┬────────────────────────────┘
                                    │ short transactions
                     ┌──────────────▼───────────────┐
                     │  Postgres — source of truth  │
                     │  slots · leases · sessions   │
                     │  profiles · checkpoints      │
                     └──────────────▲───────────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       │  Scheduler                                control plane │
       │  dispatcher · lease reaper · reconciliation             │
       └────────────────────────────┬────────────────────────────┘
                                    │ internal HTTP: start · release · state
       ┌────────────────────────────▼────────────────────────────┐
       │  Browser worker                              data plane │
       │  Chromium · CDP · screencast · downloads · recordings   │
       └─────────────────────────────────────────────────────────┘
```

## Read in this order

| Document | Question it answers |
| --- | --- |
| [Planes and responsibilities](planes.md) | Who owns which truth, and which process may do what |
| [Browser lifecycle](browser-lifecycle.md) | Slot vs. runtime vs. lease, and how fencing keeps them honest |
| [Acquiring a browser](acquiring-a-browser.md) | What happens when the pool is full and a caller waits |
| [Session state](session-state.md) | Why authentication and browser state are two documents |

Status markers: sections marked **planned** describe the target in
`REQUEST_CONCEPT.md`; everything else is in the code today.
