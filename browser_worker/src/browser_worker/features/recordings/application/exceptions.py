from browser_worker.exceptions import BrowserWorkerException


class RecordingNotFoundException(BrowserWorkerException):
    message = "Recording not found"


class RecordingAlreadyRunningException(BrowserWorkerException):
    message = "Browser is already being recorded"


class RecordingNotRunningException(BrowserWorkerException):
    message = "Recording has already been stopped"


class RecordingNotCompletedException(BrowserWorkerException):
    message = "Recording has no video available"


class RecordingFailedException(BrowserWorkerException):
    message = "Screen recording failed"


class RecordingHasSegmentsException(BrowserWorkerException):
    message = "Recording spans several tabs; download its segments instead"
