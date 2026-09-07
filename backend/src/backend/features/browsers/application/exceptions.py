from backend.exceptions import BackendException


class BrowserNotFoundException(BackendException):
    message = "Browser not found"


class BrowserUnavailableException(BackendException):
    message = "Browser is not available"


class BrowserProvisioningException(BackendException):
    message = "The browser could not be provisioned on its worker"


class WorkerRecoveryException(BackendException):
    message = "The browser worker could not be replaced"
