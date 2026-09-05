from backend.exceptions import BackendException


class NoBrowserAvailableException(BackendException):
    message = "No browser is currently available"
