from browser_worker.features.recordings.application.models import Recording
from browser_worker.features.recordings.presentation.schemas import RecordingResponse


def to_recording_response(recording: Recording) -> RecordingResponse:
    return RecordingResponse(
        id=recording.id,
        browser_id=recording.browser_id,
        state=recording.state,
        started_at=recording.started_at,
        stopped_at=recording.stopped_at,
        size_bytes=recording.size_bytes,
    )
