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

uv run httpxgen schemas/data_plane-openapi.json generated/src/generated/data_plane \
  --package-name generated.data_plane "$@"
