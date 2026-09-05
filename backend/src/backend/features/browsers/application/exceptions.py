from backend.exceptions import BackendException


class BrowserNotFoundException(BackendException):
    message = "Browser not found"


class BrowserUnavailableException(BackendException):
    message = "Browser is not available"


class BrowserCapacityExhaustedException(BackendException):
    message = "Browser capacity exhausted"
