from backend.exceptions import BackendException


class RecordingNotFoundException(BackendException):
    message = "Recording not found"


class RecordingAlreadyRunningException(BackendException):
    message = "Browser is already being recorded"


class RecordingNotRunningException(BackendException):
    message = "Recording has already been stopped"


class RecordingTransferException(BackendException):
    message = "Screen recording transfer failed"
