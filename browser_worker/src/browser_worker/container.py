from collections.abc import Sequence

from dishka import AsyncContainer, Provider, make_async_container

from browser_worker.features.workspace.infrastructure import WorkspaceProvider
from browser_worker.shared.feature import Feature


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
        WorkspaceProvider(),
        *feature_providers,
        *provider_overrides,
    )
