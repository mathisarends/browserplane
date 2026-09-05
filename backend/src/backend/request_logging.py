import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

logger = logging.getLogger("backend.requests")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    """Return the request id for outbound calls made by the current request."""
    return _request_id.get()


def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _safe_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        token = _request_id.set(request_id)
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP request crashed request_id=%s method=%s path=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                (perf_counter() - started) * 1000,
            )
            raise
        finally:
            _request_id.reset(token)

        response.headers["X-Request-ID"] = request_id
        log = logger.debug if request.url.path.endswith("/health") else logger.info
        log(
            "HTTP request completed request_id=%s method=%s path=%s "
            "status_code=%d duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response


def _safe_request_id(value: str | None) -> str:
    if value:
        cleaned = value.replace("\r", "").replace("\n", "")[:128]
        if cleaned:
            return cleaned
    return str(uuid4())
