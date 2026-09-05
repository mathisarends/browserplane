FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY browser_worker/pyproject.toml browser_worker/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --frozen --no-dev --package browser-worker --no-install-project

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY browser_worker ./browser_worker
RUN uv sync --frozen --no-dev --package browser-worker

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "browser_worker.main"]
