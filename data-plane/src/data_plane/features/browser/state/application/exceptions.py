from data_plane.exceptions import DataPlaneException


class BrowserStateInvalidException(DataPlaneException):
    message = "Browser state cannot be mounted"


class BrowserStateFailedException(DataPlaneException):
    message = "Browser state operation failed"
