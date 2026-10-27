FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim@sha256:7cf77f594be8042dab6daa9fe326f90962252268b4f120a7f5dccce4d947e6c1

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml backend/pyproject.toml
COPY browser_worker/pyproject.toml browser_worker/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --locked --no-dev --package backend --no-install-workspace

COPY generated ./generated
COPY backend ./backend
RUN uv sync --locked --no-dev --package backend

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "backend.main"]
