from abc import ABC, abstractmethod

from browser_worker.features.downloads.application.models import Download


class DownloadStore(ABC):
    @abstractmethod
    async def start(self, cdp_url: str) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def list(self) -> tuple[Download, ...]: ...

    @abstractmethod
    def file(self, download_id: str) -> Download: ...

    @abstractmethod
    async def clear(self) -> None: ...

    @property
    @abstractmethod
    def is_idle(self) -> bool: ...
