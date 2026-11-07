from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import Query, Response
from fastapi_canon import CanonResponse, CanonRouter, ErrorRegistry

from browser_worker.features.browser.presentation.errors import BROWSER_NOT_FOUND
from browser_worker.features.state.application import BrowserStateService
from browser_worker.features.state.presentation.errors import (
    BROWSER_STATE_FAILED,
    BROWSER_STATE_INVALID,
)
from browser_worker.features.state.presentation.schemas import (
    AuthenticationStateSchema,
    BrowserStateSchema,
)

_ROUTE_ERRORS = ErrorRegistry(
    name="state-routes",
    errors=(
        BROWSER_NOT_FOUND,
        BROWSER_STATE_INVALID,
        BROWSER_STATE_FAILED,
    ),
)

browser_state_router = CanonRouter(
    tags=["browser-state"],
    route_class=DishkaRoute,
    error_registry=_ROUTE_ERRORS,
    raises=(BROWSER_NOT_FOUND, BROWSER_STATE_INVALID, BROWSER_STATE_FAILED),
)


@browser_state_router.get(
    "/browser/state",
    operation_id="capture_browser_state",
)
async def capture_browser_state(
    response: Response,
    service: FromDishka[BrowserStateService],
) -> BrowserStateSchema:
    state = await service.capture_browser()
    response.headers["Cache-Control"] = "no-store"
    return state


@browser_state_router.put(
    "/browser/state",
    response=CanonResponse.empty(),
    operation_id="mount_browser_state",
)
async def mount_browser_state(
    state: BrowserStateSchema,
    service: FromDishka[BrowserStateService],
) -> None:
    await service.mount_browser(state)


@browser_state_router.get(
    "/browser/authentication-state",
    operation_id="capture_authentication_state",
)
async def capture_authentication_state(
    response: Response,
    service: FromDishka[BrowserStateService],
    origins: Annotated[
        list[str] | None,
        Query(description="Extra origins to read localStorage from"),
    ] = None,
) -> AuthenticationStateSchema:
    """Read cookies and origin-localStorage independently of open tabs.

    The response carries live session cookies and tokens, so it must not be
    cached anywhere on the way back to the caller.
    """
    state = await service.capture_authentication(origins if origins is not None else ())
    response.headers["Cache-Control"] = "no-store"
    return state


@browser_state_router.put(
    "/browser/authentication-state",
    response=CanonResponse.empty(),
    operation_id="mount_authentication_state",
)
async def mount_authentication_state(
    state: AuthenticationStateSchema,
    service: FromDishka[BrowserStateService],
) -> None:
    await service.mount_authentication(state)
