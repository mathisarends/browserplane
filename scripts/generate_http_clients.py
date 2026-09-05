"""Export the FastAPI OpenAPI documents and render the Python clients with httpxgen."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from httpxgen import GenerationError, load_openapi, write_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "schemas"
OUTPUT_DIR = PROJECT_ROOT / "generated" / "src" / "generated"


@dataclass(frozen=True, slots=True)
class ClientTarget:
    """One FastAPI application rendered into one httpxgen client package."""

    package: str
    app: str

    @property
    def schema_name(self) -> str:
        return f"{self.package}-openapi.json"

    @property
    def package_name(self) -> str:
        return f"generated.{self.package}"


TARGETS = (
    ClientTarget(package="data_plane", app="data_plane.app"),
    ClientTarget(package="control_plane", app="control_plane.app"),
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the typed Python HTTP clients for the internal APIs."
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--schemas", type=Path, default=SCHEMA_DIR)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)

    changed: list[Path] = []
    try:
        for target in TARGETS:
            schema_path = arguments.schemas / target.schema_name
            if not arguments.check:
                _write_schema(schema_path, _openapi_document(target))
            spec = load_openapi(schema_path)
            changed.extend(
                write_client(
                    spec=spec,
                    package_dir=arguments.output / target.package,
                    package_name=target.package_name,
                    check=arguments.check,
                )
            )
    except GenerationError as error:
        parser.exit(1, f"error: {error}\n")

    for path in changed:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")
    if not changed:
        print("Python HTTP clients are up to date")
    return 0


def _openapi_document(target: ClientTarget) -> dict[str, Any]:
    module = import_module(target.app)
    return module.create_app().openapi()


def _write_schema(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    raise SystemExit(main())
