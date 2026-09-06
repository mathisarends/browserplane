from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fakes.session_repositories import (
    InMemoryAuthenticationProfileRepository,
    InMemoryBrowserCheckpointRepository,
    InMemorySessionRepository,
)
from fakes.session_resources import (
    FakeBrowserRuntime,
    FakeSessionBrowsers,
    FakeSessionLeases,
)

from backend.features.browsers.domain.models import Browser, BrowserSlot
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.sessions.application.exceptions import (
    AuthenticationProfileNotFoundException,
    BrowserCheckpointNotFoundException,
    DownloadNotFoundException,
    SessionNotActiveException,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import Download, Session, SessionStatus


def _active_resources() -> tuple[Browser, Lease, Session]:
    session_id = UUID(int=1)
    browser = Browser(BrowserSlot(UUID(int=2), "http://worker"), datetime.now(UTC))
    lease = Lease(
        id=session_id,
        browser_id=browser.id,
        owner_id=UUID(int=3),
        generation=4,
        state=LeaseState.ACTIVE,
        created_at=datetime.now(UTC),
        last_renewed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        reclaim_after=datetime.now(UTC) + timedelta(minutes=2),
    )
    session = Session(
        id=session_id,
        owner_id=lease.owner_id,
        status=SessionStatus.ACTIVE,
        created_at=datetime.now(UTC),
        expires_at=lease.expires_at,
    )
    return browser, lease, session


async def _service(
    session: Session,
    browser: Browser,
    lease: Lease,
    runtime: FakeBrowserRuntime,
) -> tuple[
    SessionService,
    InMemorySessionRepository,
    InMemoryBrowserCheckpointRepository,
    InMemoryAuthenticationProfileRepository,
    FakeSessionLeases,
]:
    sessions = InMemorySessionRepository()
    checkpoints = InMemoryBrowserCheckpointRepository()
    profiles = InMemoryAuthenticationProfileRepository()
    leases = FakeSessionLeases(lease)
    await sessions.save(session)
    return (
        SessionService(
            FakeSessionBrowsers(browser, remaining_capacity=2),
            leases,  # type: ignore[arg-type]
            sessions,
            checkpoints,
            profiles,
            runtime,
            suspension_ttl=timedelta(hours=1),
        ),
        sessions,
        checkpoints,
        profiles,
        leases,
    )


@pytest.mark.asyncio
async def test_active_session_exposes_its_bound_browser_and_renewed_lease() -> None:
    browser, lease, session = _active_resources()
    service, _, _, _, _ = await _service(session, browser, lease, FakeBrowserRuntime())

    resolved = await service.get_active(session.id)
    renewed = await service.renew(session.id)

    assert resolved.browser is browser
    assert resolved.lease_generation == 4
    assert renewed.expires_at is not None
    assert renewed.expires_at > lease.expires_at
    assert await service.remaining_capacity() == 2


@pytest.mark.asyncio
async def test_saved_browser_state_profiles_and_downloads_belong_to_active_session(
) -> None:
    browser, lease, session = _active_resources()
    download = Download("report", "report.csv", "https://example.com/report", 12)
    runtime = FakeBrowserRuntime(
        authentication={"cookies": [{"name": "session"}]},
        browser_state={"tabs": [{"url": "https://example.com"}]},
        downloads=(download,),
        files={download.id: b"id,name\n1,Ada\n"},
    )
    service, _, checkpoints, profiles, _ = await _service(
        session, browser, lease, runtime
    )

    profile = await service.create_authentication_profile(session.id, name="Work")
    checkpoint = await service.create_browser_checkpoint(
        session.id, authentication_profile_id=profile.id
    )
    await service.mount_authentication_profile(session.id, profile.id)
    await service.mount_browser(session.id, checkpoint.browser_state)
    filename, content = await service.download_file(session.id, download.id)

    assert filename == "report.csv"
    assert content == b"id,name\n1,Ada\n"
    assert runtime.mounted_authentication == [profile.authentication_state]
    assert runtime.mounted_browser == [checkpoint.browser_state]

    updated = await service.update_authentication_profile(
        profile.id, session_id=session.id, name="Personal"
    )
    assert updated.name == "Personal"
    assert await service.list_browser_checkpoints() == (checkpoint,)
    assert await service.list_authentication_profiles() == (updated,)

    await service.delete_browser_checkpoint(checkpoint.id)
    await service.delete_authentication_profile(profile.id)
    assert await checkpoints.list() == ()
    assert await profiles.list() == ()
    with pytest.raises(DownloadNotFoundException):
        await service.download_file(session.id, "missing")
    with pytest.raises(AuthenticationProfileNotFoundException):
        await service.get_authentication_profile(profile.id)
    with pytest.raises(BrowserCheckpointNotFoundException):
        await service.get_browser_checkpoint(checkpoint.id)


@pytest.mark.asyncio
async def test_suspending_captures_state_then_releases_the_active_lease() -> None:
    browser, lease, session = _active_resources()
    runtime = FakeBrowserRuntime(
        authentication={"cookies": [{"name": "session"}]},
        browser_state={"tabs": [{"url": "https://example.com"}]},
    )
    service, sessions, checkpoints, profiles, leases = await _service(
        session, browser, lease, runtime
    )

    suspended = await service.suspend(session.id)

    assert suspended.session.status is SessionStatus.SUSPENDED
    assert suspended.browser_id is None
    assert leases.released == [(session.id, "session_suspended")]
    checkpoint = await service.get_browser_checkpoint(
        suspended.session.browser_checkpoint_id
    )
    assert checkpoint.browser_state == runtime.browser_state
    assert checkpoint.authentication_profile_id is not None
    assert (await profiles.list())[0].authentication_state == runtime.authentication
    stored = await sessions.get_by_id(session_id=session.id)
    assert stored is not None
    assert stored.status is SessionStatus.SUSPENDED


@pytest.mark.asyncio
async def test_listing_expires_parked_sessions_and_reaping_closes_active_ones() -> None:
    browser, lease, active = _active_resources()
    expired = Session(
        id=uuid4(),
        owner_id=active.owner_id,
        status=SessionStatus.SUSPENDED,
        created_at=datetime.now(UTC) - timedelta(hours=2),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    service, sessions, _, _, leases = await _service(
        active, browser, lease, FakeBrowserRuntime()
    )
    await sessions.save(expired)

    listed = await service.list(owner_id=active.owner_id)
    leases.reaped = (active.id, uuid4())
    released = await service.reap_expired()

    assert [item.session.status for item in listed] == [
        SessionStatus.ACTIVE,
        SessionStatus.CLOSED,
    ]
    assert released == leases.reaped
    reaped = await sessions.get_by_id(session_id=active.id)
    assert reaped is not None
    assert reaped.status is SessionStatus.CLOSED
    with pytest.raises(SessionNotActiveException):
        await service.get_active(expired.id)
