from control_plane.exceptions import ControlPlaneException


class BrowserNotFoundException(ControlPlaneException):
    message = "Browser not found"


class BrowserUnavailableException(ControlPlaneException):
    message = "Browser is not available"


class BrowserCapacityExhaustedException(ControlPlaneException):
    message = "Browser capacity exhausted"
