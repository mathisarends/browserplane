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


def error_contracts() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--locked",
            "python",
            "-m",
            "fastapi_canon.check_error_contracts",
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
        choices=("all", "lint", "test", "contracts", "build", "browser"),
    )
    mode = parser.parse_args().mode
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
