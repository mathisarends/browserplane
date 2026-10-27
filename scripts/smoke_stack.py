"""Run the UI smoke against an isolated real database, worker and scheduler."""

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
POSTGRES = (
    "postgres:17-alpine@"
    "sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b"
)
MINIO = (
    "minio/minio@"
    "sha256:14cea493d9a34af32f524e538b8346cf79f3321eff8e708c1e2960462bd8936e"
)
MC = "minio/mc@sha256:a7fe349ef4bd8521fb8497f55c6042871b2ae640607cf99d9bede5e9bdf11727"
FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def command(*args, **kwargs):
    return subprocess.check_output(
        args, text=True, creationflags=FLAGS, **kwargs
    ).strip()


def ready(url, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"Service did not become ready: {url}")


def main():
    logs = ROOT / ".pytest_cache" / "stack-smoke"
    logs.mkdir(parents=True, exist_ok=True)
    processes = []
    containers = []
    handles = []
    network = "browserplane-canon-" + str(os.getpid())
    command("docker", "network", "create", network)
    try:
        postgres = command(
            "docker",
            "run",
            "--detach",
            "--rm",
            "--network",
            network,
            "-e",
            "POSTGRES_USER=browser",
            "-e",
            "POSTGRES_PASSWORD=browser",
            "-e",
            "POSTGRES_DB=browser",
            "-p",
            "127.0.0.1::5432",
            POSTGRES,
        )
        containers.append(postgres)
        deadline = time.monotonic() + 60
        while True:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    postgres,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "browser",
                    "-d",
                    "browser",
                ],
                capture_output=True,
                creationflags=FLAGS,
                check=False,
            )
            if result.returncode == 0:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Postgres did not become ready")
            time.sleep(0.1)
        storage = command(
            "docker",
            "run",
            "--detach",
            "--rm",
            "--network",
            network,
            "--network-alias",
            "storage",
            "-e",
            "MINIO_ROOT_USER=smoke-access",
            "-e",
            "MINIO_ROOT_PASSWORD=smoke-secret",
            "-p",
            "127.0.0.1::9000",
            MINIO,
            "server",
            "/data",
        )
        containers.append(storage)
        database_port = command("docker", "port", postgres, "5432/tcp").rsplit(":", 1)[
            1
        ]
        storage_port = command("docker", "port", storage, "9000/tcp").rsplit(":", 1)[1]
        ready(f"http://127.0.0.1:{storage_port}/minio/health/live")
        command(
            "docker",
            "run",
            "--rm",
            "--network",
            network,
            "--entrypoint",
            "/bin/sh",
            MC,
            "-c",
            "mc alias set smoke http://storage:9000 smoke-access smoke-secret "
            "&& mc mb smoke/browser-smoke",
        )
        encryption_key = Fernet.generate_key().decode()
        environment = {
            **os.environ,
            "BACKEND_DATABASE_URL": f"postgresql+asyncpg://browser:browser@127.0.0.1:{database_port}/browser",
            "BACKEND_AUTHENTICATION_STATE_ENCRYPTION_KEY": encryption_key,
            "BACKEND_BROWSER_POOL_WORKER_URLS": "http://127.0.0.1:18011",
            "BROWSER_WORKER_PUBLIC_BASE_URL": "ws://127.0.0.1:18011",
            "BROWSER_WORKER_HEADLESS": "true",
            "BROWSERPLANE_API_URL": "http://127.0.0.1:18000",
            "STORAGE_BUCKET": "browser-smoke",
            "STORAGE_ENDPOINT": f"http://127.0.0.1:{storage_port}",
            "STORAGE_ACCESS_KEY": "smoke-access",
            "STORAGE_SECRET_KEY": "smoke-secret",
        }
        if executable := os.environ.get("BROWSER_EXECUTABLE"):
            environment["BROWSER_WORKER_EXECUTABLE"] = executable
        command(
            "uv",
            "run",
            "--locked",
            "--directory",
            str(ROOT / "backend"),
            "alembic",
            "upgrade",
            "head",
            env=environment,
        )
        services = [
            (
                "worker",
                [
                    "-m",
                    "uvicorn",
                    "browser_worker.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18011",
                ],
            ),
            (
                "backend",
                [
                    "-m",
                    "uvicorn",
                    "backend.app:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "18000",
                ],
            ),
            ("scheduler", ["-m", "backend.scheduler"]),
        ]
        for name, args in services:
            handle = (logs / f"{name}.log").open("w", encoding="utf-8")
            handles.append(handle)
            processes.append(
                subprocess.Popen(
                    ["uv", "run", "--locked", "python", *args],
                    cwd=ROOT,
                    env=environment,
                    stdout=handle,
                    stderr=handle,
                    creationflags=FLAGS,
                )
            )
        ready("http://127.0.0.1:18011/api/v1/health")
        ready("http://127.0.0.1:18000/api/v1/health")
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        result = subprocess.run(
            [npm, "--prefix", "frontend", "run", "test:browser"],
            cwd=ROOT,
            env=environment,
            timeout=180,
            creationflags=FLAGS,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        result.check_returncode()
    finally:
        for process in reversed(processes):
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/pid", str(process.pid), "/t", "/f"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=FLAGS,
                    check=False,
                )
            else:
                process.terminate()
            process.wait(timeout=15)
        for handle in handles:
            handle.close()
        for container in containers:
            subprocess.run(
                ["docker", "rm", "--force", container],
                stdout=subprocess.DEVNULL,
                check=False,
                creationflags=FLAGS,
            )
        subprocess.run(
            ["docker", "network", "rm", network],
            stdout=subprocess.DEVNULL,
            check=False,
            creationflags=FLAGS,
        )


if __name__ == "__main__":
    main()
