"""Export the FastAPI OpenAPI documents that httpxgen renders clients from."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "schemas"


@dataclass(frozen=True, slots=True)
class OpenAPITarget:
    """One FastAPI application whose OpenAPI document gets exported."""

    package: str
    app: str

    @property
    def schema_name(self) -> str:
        return f"{self.package}-openapi.json"


TARGETS = (
    OpenAPITarget(package="backend", app="backend.app"),
    OpenAPITarget(package="browser_worker", app="browser_worker.app"),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the FastAPI OpenAPI documents to schemas/*.json."
    )
    parser.add_argument("--schemas", type=Path, default=SCHEMA_DIR)
    arguments = parser.parse_args(argv)

    arguments.schemas.mkdir(parents=True, exist_ok=True)
    for target in TARGETS:
        module = import_module(target.app)
        document = module.create_app().openapi()
        path = arguments.schemas / target.schema_name
        path.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
