from backend.exceptions import BackendException


class NoBrowserAvailableException(BackendException):
    message = "No browser is currently available"


class SessionNotActiveException(BackendException):
    message = "Session holds no browser"


class SessionNotSuspendedException(BackendException):
    message = "Session is not suspended"


class BrowserStateTransferException(BackendException):
    message = "Could not transfer the browser state"


class DownloadNotFoundException(BackendException):
    message = "Download not found"


class AuthenticationProfileNotFoundException(BackendException):
    message = "Authentication profile not found"


class BrowserCheckpointNotFoundException(BackendException):
    message = "Browser checkpoint not found"


class SessionNotFoundException(BackendException):
    message = "Session not found"
