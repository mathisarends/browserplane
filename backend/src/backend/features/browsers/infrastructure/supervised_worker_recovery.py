import asyncio
import logging
from typing import Any, cast

from fastapi import status
from httpx2 import AsyncClient

from backend.features.browsers.application.exceptions import WorkerRecoveryException
from backend.features.browsers.application.ports import WorkerRecovery
from backend.features.browsers.domain.models import BrowserSlot, WorkerIncarnation
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from generated.browser_worker import (
    ApiError,
    GeneratedBrowserWorkerClient,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class SupervisedWorkerRecovery(WorkerRecovery):
    """Replace a worker by retiring its process and awaiting its successor.

    The worker ends itself and whatever supervises it - a container restart
    policy, a pod, a process supervisor - starts the replacement. That is the
    cleanest recovery under `one worker = one browser`: the single runtime and
    every handle a retry could not reach die with the process.
    """

    def __init__(self, http: AsyncClient, settings: BrowserWorkerSettings) -> None:
        self._http = http
        self._settings = settings

    async def replace(self, slot: BrowserSlot) -> WorkerIncarnation:
        # One budget for the whole exchange. A worker that stalls on the
        # request to step down is exactly the kind that never comes back.
        try:
            async with asyncio.timeout(self._settings.replacement_timeout_seconds):
                retiring = await self._retire(slot)
                incarnation = await self._await_successor(slot, retiring)
        except TimeoutError as error:
            raise WorkerRecoveryException(
                "The replacement browser worker did not become ready"
            ) from error
        logger.warning(
            "Browser worker replaced browser_id=%s worker=%s instance_id=%s",
            slot.id,
            slot.browser_worker_url,
            incarnation.instance_id,
        )
        return incarnation

    async def _retire(self, slot: BrowserSlot) -> WorkerIncarnation | None:
        """Ask the worker to end itself, and name the instance that answered."""
        try:
            retiring = await self._client(slot).restart_worker()
        except ApiError as error:
            if error.status_code == status.HTTP_409_CONFLICT:
                raise WorkerRecoveryException(
                    "The browser worker runs without a restart policy"
                ) from error
            raise
        except Exception:
            # Nothing answered, so nothing can be told apart either: any worker
            # that reports itself ready from here on is a new process, and one
            # that never does runs into the replacement timeout.
            logger.warning(
                "Browser worker did not accept its restart browser_id=%s worker=%s",
                slot.id,
                slot.browser_worker_url,
                exc_info=True,
            )
            return None
        return WorkerIncarnation(retiring.instance_id)

    async def _await_successor(
        self, slot: BrowserSlot, retiring: WorkerIncarnation | None
    ) -> WorkerIncarnation:
        poll_seconds = self._settings.readiness_poll_seconds
        while True:
            ready = await self._ready_incarnation(slot, timeout=poll_seconds)
            if ready is not None and ready != retiring:
                return ready
            await asyncio.sleep(poll_seconds)

    async def _ready_incarnation(
        self, slot: BrowserSlot, *, timeout: float
    ) -> WorkerIncarnation | None:
        """A worker that can hold a browser again, or nothing worth waiting on."""
        try:
            health = await self._client(slot).readiness(timeout=timeout)
        except Exception:
            return None
        if health.status is not HealthStatus.OK:
            return None
        return WorkerIncarnation(health.instance_id)

    def _client(self, slot: BrowserSlot) -> GeneratedBrowserWorkerClient:
        return GeneratedBrowserWorkerClient(
            cast(Any, self._http),
            slot.browser_worker_url,
            timeout=self._settings.request_timeout_seconds,
        )
