FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim@sha256:7cf77f594be8042dab6daa9fe326f90962252268b4f120a7f5dccce4d947e6c1

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY browser_worker/pyproject.toml browser_worker/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --locked --no-dev --package browser-worker --no-install-workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY browser_worker ./browser_worker
RUN uv sync --locked --no-dev --package browser-worker

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "browser_worker.main"]
