FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY browsertunnel/pyproject.toml browsertunnel/pyproject.toml
COPY data-plane/pyproject.toml data-plane/pyproject.toml
RUN uv sync --frozen --no-dev --package browsertunnel --no-install-project

COPY browsertunnel ./browsertunnel

RUN uv sync --frozen --no-dev --package browsertunnel

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "browsertunnel.main"]
