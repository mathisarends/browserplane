class BackendException(Exception):
    """Application failure that carries a client-safe message."""

    message = "Unexpected error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or type(self).message
        super().__init__(self.message)


class UpstreamUnavailableException(BackendException):
    """An internal plane could not be reached or answered unintelligibly."""

    message = "Upstream service unavailable"
