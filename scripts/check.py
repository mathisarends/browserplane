"""Run workspace checks in separate processes, as required by the Canon stack."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NPM = "npm.cmd" if sys.platform == "win32" else "npm"


def run(*command: str) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def architecture(*options: str) -> None:
    for config in ("smelt.yml", "browser_worker/smelt.yml"):
        run(
            "uv",
            "run",
            "--locked",
            "smelt",
            "check",
            "--config",
            config,
            "--fail-on",
            "warning",
            *options,
        )


def error_contracts() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "fastapi-canon",
            "check",
            "errors",
            "backend/src",
            "browser_worker/src",
            "--strict",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    report = json.loads(result.stdout)
    print(
        f"HTTP error contracts: {report['contract_gaps']} gaps, "
        f"{report['incomplete_operations']} operations with incomplete static analysis",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=(
            "all",
            "architecture",
            "lint",
            "test",
            "contracts",
            "build",
            "browser",
        ),
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--staged", action="store_true")
    scope.add_argument("--changed", action="store_true")
    parser.add_argument("--base")
    arguments = parser.parse_args()
    mode = arguments.mode
    if (
        arguments.staged or arguments.changed or arguments.base
    ) and mode != "architecture":
        parser.error("scope options apply only to architecture checks")
    if arguments.base and not arguments.changed:
        parser.error("--base requires --changed")
    if mode in ("all", "architecture"):
        options: list[str] = []
        if arguments.staged:
            options.append("--staged")
        if arguments.changed:
            options.append("--changed")
        if arguments.base:
            options.extend(("--base", arguments.base))
        architecture(*options)
    if mode in ("all", "lint"):
        run("uv", "run", "--locked", "ruff", "check", ".")
        run("uv", "run", "--locked", "ruff", "format", "--check", ".")
    if mode in ("all", "test"):
        for member in ("backend", "browser_worker", "generated"):
            run("uv", "run", "--locked", "--directory", member, "pytest", "-q")
    if mode in ("all", "contracts"):
        error_contracts()
        run(NPM, "--prefix", "frontend", "run", "check:generated")
    if mode in ("all", "build"):
        run(NPM, "--prefix", "frontend", "run", "build")
    if mode == "browser":
        run("uv", "run", "--locked", "python", "scripts/smoke_stack.py")


if __name__ == "__main__":
    main()
