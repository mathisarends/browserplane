import asyncio
import logging
from contextlib import suppress

import asyncpg

from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.domain.models import Browser
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.leases.settings import LeaseSettings
from backend.features.session_requests.application.wakeups import Wakeups
from backend.features.session_requests.domain import RequestStatus, SessionRequest
from backend.features.session_requests.infrastructure.notifications import (
    connection_options,
)
from backend.features.session_requests.infrastructure.repository import (
    SqlSessionRequestRepository,
)
from backend.features.sessions.application.ports import BrowserRuntime
from backend.features.sessions.application.service import SessionService
from backend.infrastructure.database.settings import DatabaseSettings
from backend.shared.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)
LEADER_LOCK = 728194630


class Dispatcher:
    def __init__(
        self,
        sessions: UnitOfWork[SessionService],
        repository: SqlSessionRequestRepository,
        provisioner: BrowserProvisioner,
        runtime: BrowserRuntime,
        settings: DatabaseSettings,
        pool: BrowserPoolSettings,
        wakeups: Wakeups,
        leases: LeaseSettings,
    ):
        self._sessions = sessions
        self._repository = repository
        self._provisioner = provisioner
        self._runtime = runtime
        self._settings = settings
        self._pool = pool
        self._wakeups = wakeups
        self._leases = leases

    async def run(self):
        """Elect a leader on a dedicated connection, without a DB transaction.

        Losing leadership cancels local work. Committed reservations survive and
        are recovered by the next leader. Query-pool connections stay short lived.
        """
        while True:
            connection = None
            try:
                connection = await asyncpg.connect(
                    **connection_options(self._settings), timeout=5
                )
                elected = await connection.fetchval(
                    "SELECT pg_try_advisory_lock($1)", LEADER_LOCK
                )
                if elected:
                    logger.info("Browser scheduler elected")
                    await self._repository.reconcile(self._pool)
                    async with asyncio.TaskGroup() as group:
                        group.create_task(self._watch_leadership(connection))
                        group.create_task(self._dispatch())
                        group.create_task(self._reap())
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Browser scheduler interrupted; recovering")
            finally:
                if connection is not None:
                    with suppress(Exception):
                        await connection.close(timeout=2)
            await asyncio.sleep(2)

    async def _watch_leadership(self, connection):
        while True:
            await asyncio.sleep(1)
            await connection.execute("SELECT 1", timeout=2)

    async def _dispatch(self):
        while True:
            self._wakeups.dispatch.clear()
            claimed = await self._repository.claim()
            if claimed is not None:
                request, browser = claimed
                try:
                    async with asyncio.timeout(90):
                        await self._provision(request, browser)
                except Exception:
                    logger.exception(
                        "Session request provisioning failed request_id=%s", request.id
                    )
                    await self._repository.retry(request.id)
                continue
            with suppress(TimeoutError):
                await asyncio.wait_for(self._wakeups.dispatch.wait(), timeout=5)

    async def _provision(self, request: SessionRequest, browser: Browser):
        # Release is generation checked and idempotent. A previous scheduler may
        # have died after worker creation but before committing the assignment.
        await self._provisioner.release(browser.slot, browser.generation)
        current = await self._repository.get(request.id)
        if current.status in (RequestStatus.CANCELLED, RequestStatus.EXPIRED):
            await self._repository.cleaned(request.id, browser)
            return
        async with self._sessions() as sessions:
            checkpoint = (
                await sessions.get_browser_checkpoint(request.browser_checkpoint_id)
                if request.browser_checkpoint_id
                else None
            )
            profile_id = request.authentication_profile_id or (
                checkpoint.authentication_profile_id if checkpoint else None
            )
            profile = (
                await sessions.get_authentication_profile(profile_id)
                if profile_id
                else None
            )
        # The unit of work is closed before any worker call, so provisioning
        # never occupies a database connection while it waits on HTTP.
        await self._provisioner.start(browser.slot, browser.generation)
        await self._runtime.clear_downloads(browser)
        if profile is not None:
            await self._runtime.mount_authentication(
                browser, profile.authentication_state
            )
        if checkpoint is not None:
            await self._runtime.mount_browser(browser, checkpoint.browser_state)
        if not await self._repository.finish(request.id, browser):
            await self._provisioner.release(browser.slot, browser.generation)
            await self._repository.cleaned(request.id, browser)

    async def _reap(self):
        while True:
            try:
                async with self._sessions() as sessions:
                    await sessions.reap_expired()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Lease reaper iteration failed")
            await asyncio.sleep(self._leases.reaper_interval_seconds)
