FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY control-plane/pyproject.toml control-plane/pyproject.toml
COPY browsertunnel/pyproject.toml browsertunnel/pyproject.toml
COPY data-plane/pyproject.toml data-plane/pyproject.toml
COPY generated/pyproject.toml generated/pyproject.toml
RUN uv sync --frozen --no-dev --package control-plane --no-install-project

COPY generated ./generated
COPY control-plane ./control-plane
RUN uv sync --frozen --no-dev --package control-plane

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["python", "-m", "control_plane.main"]
