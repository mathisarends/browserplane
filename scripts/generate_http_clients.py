"""Regenerate the typed Python HTTP clients with httpxgen.

Usage:
    uv run python scripts/generate_http_clients.py          # rewrite the clients
    uv run python scripts/generate_http_clients.py --check  # fail if out of date

Python rather than shell so `npm run generate` can call it on every platform.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

import export_openapi_schemas
from httpxgen.cli import main as httpxgen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PROJECT_ROOT / "schemas" / "browser_worker-openapi.json"
OUTPUT = PROJECT_ROOT / "generated" / "src" / "generated" / "browser_worker"
PACKAGE = "generated.browser_worker"


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    exported = export_openapi_schemas.main([])
    if exported:
        return exported
    # httpxgen's CLI parses sys.argv itself and takes no argument vector.
    sys.argv = [
        "httpxgen",
        str(SCHEMA),
        str(OUTPUT),
        "--package-name",
        PACKAGE,
        *arguments,
    ]
    return httpxgen()


if __name__ == "__main__":
    raise SystemExit(main())
