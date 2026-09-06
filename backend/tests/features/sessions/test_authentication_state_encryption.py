from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.sessions.domain.models import AuthenticationProfile
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationProfileRepository,
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

    repository = SqlAuthenticationProfileRepository(session, cipher)
    profile = AuthenticationProfile(
        id=uuid4(),
        owner_id=uuid4(),
        name="Work",
        authentication_state=state,
        created_at=now,
    )
    model = repository.to_model(profile)

    assert b"sensitive-token" not in model.authentication_state
    assert repository.to_domain(model) == profile
