from browser_worker.exceptions import BrowserWorkerException


class RecordingNotFoundException(BrowserWorkerException):
    message = "Recording not found"


class RecordingAlreadyExistsException(BrowserWorkerException):
    message = "This browser session already has a recording"


class RecordingNotRunningException(BrowserWorkerException):
    message = "Recording has already been stopped"


class RecordingNotCompletedException(BrowserWorkerException):
    message = "Recording has no video available"


class RecordingFailedException(BrowserWorkerException):
    message = "Screen recording failed"
