from collections.abc import Sequence

from dishka import AsyncContainer, Provider, make_async_container

from backend.infrastructure.browser_worker import BrowserWorkerProvider
from backend.infrastructure.database import DatabaseProvider
from backend.infrastructure.storage.provider import StorageProvider
from backend.shared.feature import Feature


def create_container(
    features: Sequence[Feature],
    provider_overrides: Sequence[Provider] = (),
) -> AsyncContainer:
    overridden_types = {type(provider) for provider in provider_overrides}
    feature_providers = [
        provider_type()
        for feature in features
        for provider_type in feature.providers
        if provider_type not in overridden_types
    ]
    return make_async_container(
        *_create_core_providers(),
        *feature_providers,
        *provider_overrides,
    )


def _create_core_providers() -> tuple[Provider, ...]:
    return (
        StorageProvider(),
        DatabaseProvider(),
        BrowserWorkerProvider(),
    )
