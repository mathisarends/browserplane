FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY data-plane/pyproject.toml data-plane/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --frozen --no-dev --package data-plane --no-install-project

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY data-plane ./data-plane
RUN uv sync --frozen --no-dev --package data-plane

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "data_plane.main"]
