from backend.exceptions import BackendException


class RecordingNotFoundException(BackendException):
    message = "Recording not found"


class RecordingAlreadyExistsException(BackendException):
    message = "This browser session already has a recording"


class RecordingNotRunningException(BackendException):
    message = "Recording has already been stopped"


class RecordingTransferException(BackendException):
    message = "Screen recording transfer failed"
