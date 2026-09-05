FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY data-plane/pyproject.toml data-plane/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --frozen --no-dev --package backend --no-install-project

COPY generated ./generated
COPY backend ./backend
RUN uv sync --frozen --no-dev --package backend

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "backend.main"]
