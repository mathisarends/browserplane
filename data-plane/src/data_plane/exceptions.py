class DataPlaneException(Exception):
    """Application failure that carries a client-safe message."""

    message = "Unexpected error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or type(self).message
        super().__init__(self.message)
