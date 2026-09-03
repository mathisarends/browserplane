from data_plane.exceptions import DataPlaneException


class RecordingNotFoundException(DataPlaneException):
    message = "Recording not found"


class RecordingAlreadyRunningException(DataPlaneException):
    message = "Browser is already being recorded"


class RecordingNotRunningException(DataPlaneException):
    message = "Recording has already been stopped"


class RecordingNotCompletedException(DataPlaneException):
    message = "Recording has no video available"


class RecordingFailedException(DataPlaneException):
    message = "Screen recording failed"


class RecordingHasSegmentsException(DataPlaneException):
    message = "Recording spans several tabs; download its segments instead"
