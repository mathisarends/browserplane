import asyncio
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from dishka import AsyncContainer, Scope
from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from backend.features.browser_requests.application import ControlPlane, RequestRepository
from backend.features.browser_requests.domain import BrowserRequest, RequestConflict, RequestEnded, RequestStatus
from backend.features.sessions.application.exceptions import SessionNotSuspendedException
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import SessionStatus

router = APIRouter(route_class=DishkaRoute, tags=["browser-requests"])


class BrowserRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    status: RequestStatus
    created_at: datetime
    expires_at: datetime
    lease_id: UUID | None
    test_run_id: UUID | None


@router.get("/browser-requests/{request_id}", operation_id="get_browser_request")
async def get_browser_request(request_id: UUID, owner_id: UUID,
                              repository: FromDishka[RequestRepository]) -> BrowserRequestResponse:
    return BrowserRequestResponse.model_validate(await owned_request(repository, request_id, owner_id))


@router.delete("/browser-requests/{request_id}", operation_id="cancel_browser_request")
async def cancel_browser_request(request_id: UUID, owner_id: UUID,
                                 repository: FromDishka[RequestRepository]) -> BrowserRequestResponse:
    await owned_request(repository, request_id, owner_id)
    return BrowserRequestResponse.model_validate(await repository.end(request_id, RequestStatus.CANCELLED))


async def owned_request(repository, request_id, owner_id):
    try:
        request = await repository.get(request_id)
    except LookupError as error:
        raise HTTPException(404, "Browser request not found") from error
    if request.owner_id != owner_id:
        raise HTTPException(404, "Browser request not found")
    return request


async def acquire_session(http_request: Request, container: AsyncContainer, control: ControlPlane,
                          *, owner_id: UUID | None = None, request_id: UUID | None = None,
                          timeout_seconds: float = 60, test_run_id: UUID | None = None,
                          authentication_profile_id: UUID | None = None,
                          browser_checkpoint_id: UUID | None = None,
                          resume_session_id: UUID | None = None) -> UUID:
    existing = None
    if request_id is not None:
        repository = await container.get(RequestRepository)
        with suppress(LookupError):
            existing = await repository.get(request_id)
    if existing is not None:
        # The original operation may already have resumed the session, or its
        # saved profile may have been removed. Enqueue still checks all inputs.
        owner_id = owner_id or existing.owner_id
        if resume_session_id is not None:
            browser_checkpoint_id = existing.browser_checkpoint_id
    else:
        # Validate resources in an independent scope, released before waiting.
        async with container(scope=Scope.REQUEST) as scoped:
            sessions = await scoped.get(SessionService)
            if resume_session_id is not None:
                aggregate = await sessions.get(resume_session_id)
                if aggregate.status is not SessionStatus.SUSPENDED:
                    raise SessionNotSuspendedException()
                owner_id = aggregate.owner_id
                browser_checkpoint_id = aggregate.session.browser_checkpoint_id
            checkpoint = (await sessions.get_browser_checkpoint(browser_checkpoint_id)
                          if browser_checkpoint_id else None)
            profile_id = authentication_profile_id or (checkpoint.authentication_profile_id if checkpoint else None)
            if profile_id is not None:
                await sessions.get_authentication_profile(profile_id)
    assert owner_id is not None
    now = datetime.now(UTC)
    request = BrowserRequest(id=request_id or uuid4(), owner_id=owner_id,
        status=RequestStatus.QUEUED, created_at=now,
        expires_at=now + timedelta(seconds=timeout_seconds), test_run_id=test_run_id,
        authentication_profile_id=authentication_profile_id, browser_checkpoint_id=browser_checkpoint_id,
        resume_session_id=resume_session_id)

    async def disconnected():
        while not await http_request.is_disconnected():
            await asyncio.sleep(0.5)

    acquire = asyncio.create_task(control.acquire_browser(request))
    disconnect = asyncio.create_task(disconnected())
    try:
        done, _ = await asyncio.wait((acquire, disconnect), return_when=asyncio.FIRST_COMPLETED)
        if acquire in done:
            return acquire.result()
        raise HTTPException(499, "Browser request disconnected")
    except RequestConflict as error:
        raise HTTPException(409, str(error)) from error
    except RequestEnded as error:
        raise HTTPException(408 if error.request.status is RequestStatus.EXPIRED else 409,
                            {"request_id": str(request.id), "status": error.request.status}) from error
    finally:
        acquire.cancel()
        disconnect.cancel()
        await asyncio.gather(acquire, disconnect, return_exceptions=True)
