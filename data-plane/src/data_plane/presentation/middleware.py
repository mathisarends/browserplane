import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("data_plane.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _safe_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
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
