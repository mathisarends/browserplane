from collections import defaultdict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Annotated, Any, Union

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from control_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


@dataclass(frozen=True, slots=True)
class ApiErrorSpec:
    """Binds application exceptions to a documented HTTP error response."""

    exceptions: tuple[type[Exception], ...]
    status_code: int
    code: ApiErrorCode
    response_model: type[ApiErrorResponse]
    description: str


def api_error_responses(*specs: ApiErrorSpec) -> dict[int | str, dict[str, Any]]:
    """Build the OpenAPI ``responses`` mapping for the given error specs."""
    grouped: dict[int, list[ApiErrorSpec]] = defaultdict(list)
    for spec in specs:
        grouped[spec.status_code].append(spec)

    return {
        status_code: {
            "model": _response_model(group),
            "description": " | ".join(spec.description for spec in group),
        }
        for status_code, group in grouped.items()
    }


def register_api_error_handlers(app: FastAPI, specs: Iterable[ApiErrorSpec]) -> None:
    """Translate application exceptions into their API error responses."""
    for spec in specs:
        handler = _handler(spec)
        for exception in spec.exceptions:
            app.add_exception_handler(exception, handler)


def _response_model(group: list[ApiErrorSpec]) -> Any:
    models = tuple(spec.response_model for spec in group)
    if len(models) == 1:
        return models[0]
    return Annotated[Union[models], Field(discriminator="code")]  # noqa: UP007


def _handler(
    spec: ApiErrorSpec,
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handle(request: Request, error: Exception) -> JSONResponse:
        body = spec.response_model(code=spec.code, message=str(error))
        return JSONResponse(status_code=spec.status_code, content=body.model_dump())

    return handle
