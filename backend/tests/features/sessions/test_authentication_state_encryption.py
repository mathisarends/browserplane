from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.sessions.application.models import (
    AuthenticationStateSnapshot,
    SuspendedSession,
)
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationStateSnapshotRepository,
    SqlSuspendedSessionRepository,
)

ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


def test_repositories_encrypt_authentication_state_at_the_database_boundary() -> None:
    cipher = AuthenticationStateCipher(ENCRYPTION_KEY)
    session = cast(AsyncSession, object())
    state = {
        "cookies": [{"name": "session", "value": "sensitive-token"}],
        "localStorage": [],
    }
    now = datetime.now(UTC)

    snapshot_repository = SqlAuthenticationStateSnapshotRepository(session, cipher)
    snapshot = AuthenticationStateSnapshot(
        id=uuid4(),
        owner_id=uuid4(),
        name="Work",
        authentication_state=state,
        created_at=now,
    )
    snapshot_model = snapshot_repository.to_model(snapshot)

    suspension_repository = SqlSuspendedSessionRepository(session, cipher)
    suspension = SuspendedSession(
        id=uuid4(),
        owner_id=uuid4(),
        authentication_state=state,
        browser_state={"tabs": [], "active_tab_index": 0},
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    suspension_model = suspension_repository.to_model(suspension)

    assert b"sensitive-token" not in snapshot_model.authentication_state
    assert b"sensitive-token" not in suspension_model.authentication_state
    assert snapshot_repository.to_domain(snapshot_model) == snapshot
    assert suspension_repository.to_domain(suspension_model) == suspension
