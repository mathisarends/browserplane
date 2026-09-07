from collections.abc import Sequence
from uuid import UUID, uuid5

from backend.features.browsers.application.ports import BrowserWorkerDirectory
from backend.features.browsers.domain.models import BrowserWorker
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings

WORKER_NAMESPACE = UUID("8499344b-3ea4-4fc4-b55f-5233d87d3db9")


class StaticBrowserWorkerDirectory(BrowserWorkerDirectory):
    """The workers named in the configuration, and no others.

    A configured URL is what stays the same across restarts here, so it is the
    identity the worker id is derived from. Repointing a worker at a new URL
    therefore retires the old worker and introduces a new one.
    """

    def __init__(self, settings: BrowserPoolSettings) -> None:
        self._settings = settings

    async def snapshot(self) -> Sequence[BrowserWorker]:
        return tuple(
            BrowserWorker(uuid5(WORKER_NAMESPACE, url), url)
            for url in self._settings.worker_urls
        )
