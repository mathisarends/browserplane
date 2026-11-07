# Python architecture policy

`smelt-cli==0.5.0` is pinned in the development environment and lockfile.
`smelt.base.yml` selects the shared rules. `smelt.yml` governs the backend;
`browser_worker/smelt.yml` governs the worker. Both run from `scripts/check.py`,
the staged pre-commit hook, and the existing CI workflow.

```console
uv run --locked python scripts/check.py architecture
uv run --locked python scripts/check.py architecture --changed --base origin/main
uv run --locked smelt context backend.features.sessions
uv run --locked smelt context browser_worker.features.downloads --config browser_worker/smelt.yml
uv run --locked pre-commit run --all-files
```

The full check uses `--fail-on warning`. Changed and staged checks support the
editing loop; they do not replace the full CI check. Both policies require strict
coverage: every production module needs a role. The root policy explicitly
delegates the worker to its own policy. Generated HTTP clients are excluded from
handwritten-code conventions and verified through generation and drift checks.
Smelt currently supports one feature root per policy, which is why the services
have separate configurations sharing one base.

## Layers and domains

| Layer | Allowed dependencies | Responsibility |
| --- | --- | --- |
| Domain | Standard library and explicitly permitted downstream domain types | Entities, records and ports |
| Application | Domain and explicitly permitted application APIs | Use cases, validation and coordination |
| Infrastructure | Domain, application and infrastructure | CDP, HTTP, SQL, filesystem adapters and environment loading |
| Presentation | Domain, application and presentation | HTTP/RPC contracts, DTOs and WebSocket adapters |

Domain forbids third-party imports. Application permits Pydantic for validated
policies and state documents, while excluding FastAPI, Dishka, SQLAlchemy,
environment loading and transport clients. Provider modules and `feature.py`
are explicit wiring boundaries. App creation, lifespans and scheduler startup
are composition roots. Ordinary modules cannot import those roots or providers.
Type-checking imports participate in boundary and concrete module-cycle checks.
Transitive analysis prevents facades from hiding forbidden dependencies.

Cross-feature dependencies are denied unless a named feature/layer pair appears
in the service policy. Session requests depend on sessions, sessions depend on
leases and browsers, and leases depend on browsers. Admin coordinates those
downstream APIs; session presentation uses the browser-tunnel adapter.
Recordings use the browser API. The worker's browser/workspace and screencast
APIs support downloads, state and recordings; release coordinates their cleanup.
Allowances also state the reachable downstream layers required by transitive
analysis. They do not grant every feature access to every application service.

Domain and application packages expose deliberate `__init__.py` APIs with
`__all__`. Consumers outside a layer package use those facades; implementation
modules import their own siblings directly to avoid initialization cycles.
Feature contracts expose those layers, feature declarations, provider modules
for composition, and the specific reusable presentation contracts. The backend
scheduler and lifespan also consume the session-request dispatcher/listener as
explicit infrastructure entry points.

## Source and test conventions

The policy selects every Smelt 0.5.0 rule except the mutually exclusive
require/forbid module-docstring conventions. Parameterized rules have explicit
policies where applicable: absolute imports, descriptive module names, no private
module prefixes or future annotations, public definitions before private helpers,
caller before callee, deliberate facade exports, and match/case for type dispatch.
Stateless helpers belong at module scope. Constructor-only Dishka factories use
direct `provide(...)` registrations. Instance fields use separate assignments.

Internal-only members and symbols are private. Optional defaults distinguish
`None` from explicit falsy values. Secret settings use secret types. Test checks
cover outcome evidence, await assertions, bounded waits, deterministic data,
private access, patch targets and excessive patches. Domain tests forbid mocks.
Unit tests mirror their source module; the backend application scenario and
worker browser integration suite are deliberate integration exceptions. This
policy does not require a test for every module or freeze evolving HTTP payloads.

All findings except `deep-object-navigation` fail at warning severity or above.
That rule remains advisory: cdpify's `session.input`, `session.page` and
`client.target` are intentional protocol namespaces, and standard subprocess
pipes and workspace paths are boundary APIs. Its current findings were reviewed;
new application collaborator chains still require architectural review.

Narrow suppressions retain documented ASGI/schema-export factories, settings
factories whose constructors consume environment options rather than DI services,
and one existing lifecycle smoke test whose outcome is completion without an
exception. Boundary, coverage and cycle rules have no suppressions or debt file.

## Corrections made during adoption

- Lease errors no longer inherit session errors. The session application maps
  downstream lease failures explicitly into its own public exception vocabulary.
- Heartbeats use the application-owned `UnitOfWork[SessionService]` port; the
  Dishka container stays in infrastructure wiring.
- Browser-tunnel presentation receives a browser factory. Frame packaging and
  advertised browser endpoints are supplied through application-owned interfaces.
- Download orchestration depends on `DownloadStore`; CDP collection lives in an
  infrastructure adapter. Failed startup awaits canceled listeners before
  disconnecting the client.
- Workspace filesystem operations and process-restart timers/signals sit behind
  application-owned ports. Their concrete implementations live in infrastructure;
  restart tests supply a fake port instead of overriding a private service hook.
- Routers own their error catalogs rather than importing a central union of
  unrelated feature errors. Missing operation declarations are now explicit.
- SQL records store browser states as strings; repositories translate to/from
  domain enums. Backend HTTP DTOs no longer depend on generated worker models.
- Provider re-exports, unused browser-reset code and duplicate worker-container
  construction were removed. Test paths, IDs and timeout guards were corrected.

The existing contract checker still reports incomplete static analysis of dynamic
adapters and external calls. Zero reported gaps and complete Smelt policy coverage
do not prove every runtime path; tests and generated-client checks run alongside
the architecture checks.
