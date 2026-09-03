# Agent Guidelines

## Testing

The project and its APIs are still evolving. Do not write extensive tests unless
the user explicitly asks for them. Add only the smallest smoke test needed to
validate that changed code imports, starts, and runs successfully.

Avoid locking down endpoint payloads, status codes, edge cases, or other API
contracts that are still being explored. Prefer lightweight validation with the
existing test suite, linting, type checks, or a direct startup/import check over
adding broad new test coverage.
