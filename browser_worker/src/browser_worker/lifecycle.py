class Lifecycle:
    def __init__(self) -> None:
        self._draining = False

    @property
    def is_draining(self) -> bool:
        return self._draining

    def start_draining(self) -> None:
        self._draining = True
