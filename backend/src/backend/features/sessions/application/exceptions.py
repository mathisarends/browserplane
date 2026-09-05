from backend.exceptions import BackendException


class SessionNotFoundException(BackendException):
    message = "Session not found"


class SessionExpiredException(BackendException):
    message = "Session has expired"


class NoBrowserAvailableException(BackendException):
    message = "No browser is currently available"
