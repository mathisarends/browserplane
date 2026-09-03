FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY browsertunnel/pyproject.toml browsertunnel/pyproject.toml
COPY control-plane/pyproject.toml control-plane/pyproject.toml
RUN uv sync --frozen --no-dev --package browsertunnel --no-install-project

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium \
    && rm -rf /var/lib/apt/lists/*

COPY browsertunnel ./browsertunnel

RUN uv sync --frozen --no-dev --package browsertunnel

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "browsertunnel.main"]
