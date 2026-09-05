from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status

from data_plane.features.browser_state.application.service import BrowserStateService
from data_plane.features.browser_state.presentation.errors import (
    BROWSER_STATE_FAILED,
    BROWSER_STATE_INVALID,
)
from data_plane.features.browser_state.presentation.mapper import (
    to_browser_state,
    to_browser_state_response,
)
from data_plane.features.browser_state.presentation.schemas import BrowserStateSchema
from data_plane.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from data_plane.presentation.api_errors import api_error_responses

browser_state_router = APIRouter(tags=["browser-state"], route_class=DishkaRoute)


@browser_state_router.get(
    "/browser/{browser_id}/state",
    operation_id="capture_browser_state",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        BROWSER_STATE_INVALID,
        BROWSER_STATE_FAILED,
    ),
)
async def capture_browser_state(
    browser_id: UUID,
    response: Response,
    service: FromDishka[BrowserStateService],
    origins: Annotated[
        list[str] | None,
        Query(description="Extra origins to read localStorage from"),
    ] = None,
) -> BrowserStateSchema:
    """Read the browser's tabs and authentication state.

    The response carries live session cookies and tokens, so it must not be
    cached anywhere on the way back to the caller.
    """
    state = await service.capture(browser_id, origins or ())
    response.headers["Cache-Control"] = "no-store"
    return to_browser_state_response(state)


@browser_state_router.put(
    "/browser/{browser_id}/state",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="mount_browser_state",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        BROWSER_STATE_INVALID,
        BROWSER_STATE_FAILED,
    ),
)
async def mount_browser_state(
    browser_id: UUID,
    state: BrowserStateSchema,
    service: FromDishka[BrowserStateService],
) -> Response:
    """Replace the browser's state with a previously captured one."""
    await service.mount(browser_id, to_browser_state(state))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
