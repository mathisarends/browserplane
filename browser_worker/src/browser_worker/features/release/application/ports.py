from abc import ABC, abstractmethod


class WorkerRestarter(ABC):
    @abstractmethod
    def schedule(self, response_delay: float, shutdown_timeout: float) -> None: ...
