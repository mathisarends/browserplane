#!/usr/bin/env sh
# Regenerate the typed Python HTTP clients with httpxgen.
#
# Usage:
#   ./scripts/generate_http_clients.sh          # rewrite the clients
#   ./scripts/generate_http_clients.sh --check  # fail if out of date
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

uv run python scripts/export_openapi_schemas.py

uv run httpxgen schemas/browser_worker-openapi.json generated/src/generated/browser_worker \
  --package-name generated.browser_worker "$@"
