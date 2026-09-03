"""Export the FastAPI OpenAPI documents and render the Python clients."""

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from python_codegen import PythonClientOptions, write_python_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = PROJECT_ROOT / "schemas"
OUTPUT_DIR = PROJECT_ROOT / "generated" / "src" / "generated"


@dataclass(frozen=True, slots=True)
class ClientTarget:
    """One FastAPI application rendered into one generated subpackage."""

    package: str
    app: str
    client_name: str

    @property
    def schema_name(self) -> str:
        return f"{self.package}-openapi.json"


TARGETS = (
    ClientTarget(
        package="data_plane",
        app="data_plane.app",
        client_name="DataPlaneClient",
    ),
    ClientTarget(
        package="control_plane",
        app="control_plane.app",
        client_name="ControlPlaneClient",
    ),
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
    for target in TARGETS:
        document = _openapi_document(target)
        if not arguments.check:
            _write_schema(arguments.schemas / target.schema_name, document)
        changed.extend(
            write_python_client(
                document,
                arguments.output / target.package,
                PythonClientOptions(
                    client_name=target.client_name,
                    source=target.schema_name,
                ),
                check=arguments.check,
            )
        )

    for path in changed:
        label = "Out of date" if arguments.check else "Wrote"
        print(f"{label}: {path.relative_to(PROJECT_ROOT)}")
    if not changed:
        print("Python HTTP clients are up to date")
    return int(arguments.check and bool(changed))


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
