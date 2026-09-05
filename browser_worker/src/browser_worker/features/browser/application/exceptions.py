from browser_worker.exceptions import BrowserWorkerException


class BrowserNotFoundException(BrowserWorkerException):
    message = "Browser not found"


class BrowserAlreadyRunningException(BrowserWorkerException):
    message = "Worker already runs a browser"


class BrowserStartupException(BrowserWorkerException):
    message = "Browser failed to start"
