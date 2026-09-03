from data_plane.exceptions import DataPlaneException


class BrowserNotFoundException(DataPlaneException):
    message = "Browser not found"


class BrowserAlreadyRunningException(DataPlaneException):
    message = "Worker already runs a browser"


class BrowserStartupException(DataPlaneException):
    message = "Browser failed to start"
