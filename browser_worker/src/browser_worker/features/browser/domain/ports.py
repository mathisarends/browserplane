from abc import ABC, abstractmethod


class BrowserProcess(ABC):
    """A single browser process the worker can start and stop."""

    @abstractmethod
    def is_available(self) -> bool:
        """Report whether the browser can be started on this machine."""

    @abstractmethod
    async def start(self) -> str:
        """Start the browser and return its internal CDP endpoint."""

    @abstractmethod
    async def stop(self) -> None:
        """Terminate the browser and release its resources."""
