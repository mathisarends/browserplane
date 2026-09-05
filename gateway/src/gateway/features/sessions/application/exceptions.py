from gateway.exceptions import GatewayException


class SessionNotFoundException(GatewayException):
    message = "Session not found"


class SessionExpiredException(GatewayException):
    message = "Session has expired"


class NoBrowserAvailableException(GatewayException):
    message = "No browser is currently available"
