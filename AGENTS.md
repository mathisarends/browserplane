# Agent Guidelines

## Architecture

Smelt 0.5.0 defines the Python architecture in `smelt.yml`,
`browser_worker/smelt.yml`, and their shared `smelt.base.yml`.

Before editing, run `uv run --locked smelt context <module-or-path>`;
for worker modules add `--config browser_worker/smelt.yml`.
After editing, run
`uv run --locked python scripts/check.py architecture --changed --base origin/main`.
Before committing, stage the intended changes and run
`uv run --locked pre-commit run --all-files`.

Fix findings in the owning layer. Keep concrete adapters and environment loading
in infrastructure, framework-free domain types in domain, and orchestration in
application. Import other layers through their declared package APIs. Do not add
debt, widen feature allowances, or suppress boundary rules to make checks pass.
Reasoned exceptions for deliberate public entry points or SDK namespaces require
review; they must not conceal application coupling.

## Testing

The project and its APIs are still evolving. Do not write extensive tests unless
the user explicitly asks for them. Add only the smallest smoke test needed to
validate that changed code imports, starts, and runs successfully.

Avoid locking down endpoint payloads, status codes, edge cases, or other API
contracts that are still being explored. Prefer lightweight validation with the
existing test suite, linting, type checks, or a direct startup/import check over
adding broad new test coverage.

## Readability

Use descriptive intermediate variables for chained calls or attribute access
when they represent distinct domain steps. Do not inline such expressions
directly in a `return` merely to save a line.
