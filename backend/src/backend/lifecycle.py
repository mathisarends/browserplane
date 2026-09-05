class Lifecycle:
    def __init__(self) -> None:
        self._ready = False
        self._draining = False

    @property
    def is_ready(self) -> bool:
        return self._ready and not self._draining

    def mark_ready(self) -> None:
        self._ready = True

    def start_draining(self) -> None:
        self._draining = True
