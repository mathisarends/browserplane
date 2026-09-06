from browser_worker.exceptions import BrowserWorkerException


class BrowserStateInvalidException(BrowserWorkerException):
    message = "Browser state cannot be mounted"


class BrowserStateFailedException(BrowserWorkerException):
    message = "Browser state operation failed"
