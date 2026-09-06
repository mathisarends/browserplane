from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.features.browsers.domain.models import Browser, BrowserSlot
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.sessions.domain.models import (
    ResolvedSession,
    Session,
    SessionStatus,
)


def _active() -> tuple[Session, Lease, Browser]:
    now = datetime.now(UTC)
    browser = Browser(BrowserSlot(uuid4(), "http://worker"), now)
    session = Session(
        id=uuid4(),
        owner_id=uuid4(),
        status=SessionStatus.ACTIVE,
        created_at=now,
        expires_at=now + timedelta(minutes=1),
    )
    lease = Lease(
        id=session.id,
        browser_id=browser.id,
        owner_id=session.owner_id,
        generation=0,
        state=LeaseState.ACTIVE,
        created_at=now,
        last_renewed_at=now,
        expires_at=session.expires_at,
        reclaim_after=now + timedelta(minutes=2),
    )
    return session, lease, browser


def test_session_lifecycle_preserves_and_clears_only_relevant_state() -> None:
    session, _, _ = _active()
    checkpoint_id = uuid4()
    suspended = session.suspend(checkpoint_id, datetime.now(UTC) + timedelta(hours=1))

    assert suspended.status is SessionStatus.SUSPENDED
    assert suspended.browser_checkpoint_id == checkpoint_id
    resumed = suspended.resume(datetime.now(UTC) + timedelta(minutes=1))
    assert resumed.status is SessionStatus.ACTIVE
    assert resumed.browser_checkpoint_id is None
    assert resumed.close().close().status is SessionStatus.CLOSED
    with pytest.raises(ValueError):
        suspended.suspend(uuid4(), datetime.now(UTC))


def test_resolved_session_requires_matching_active_resources() -> None:
    session, lease, browser = _active()
    resolved = ResolvedSession.active(session, lease, browser)

    assert resolved.browser_id == browser.id
    assert resolved.lease is lease
    with pytest.raises(ValueError):
        ResolvedSession.active(session, replace(lease, id=uuid4()), browser)
    with pytest.raises(ValueError):
        ResolvedSession.inactive(session)
