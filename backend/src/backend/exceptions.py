from typing import Any


class BackendException(Exception):
    """Application failure that carries a client-safe message.

    ``details`` holds the extra fields the matching API error response declares,
    for failures a client cannot act on from the message alone.
    """

    message = "Unexpected error"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message if message is not None else type(self).message
        self.details = details if details is not None else {}
        super().__init__(self.message)
