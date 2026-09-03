from data_plane.exceptions import DataPlaneException


class BrowserNotFoundException(DataPlaneException):
    message = "Browser not found"


class BrowserCapacityExhaustedException(DataPlaneException):
    message = "Worker capacity exhausted"


class BrowserStartupException(DataPlaneException):
    message = "Browser failed to start"
