from browser_worker.features.recordings.application.models import Recording
from browser_worker.features.recordings.presentation.schemas import (
    RecordingResponse,
    RecordingSegmentResponse,
)


def to_recording_response(recording: Recording) -> RecordingResponse:
    return RecordingResponse(
        id=recording.id,
        browser_id=recording.browser_id,
        state=recording.state,
        started_at=recording.started_at,
        stopped_at=recording.stopped_at,
        size_bytes=recording.size_bytes,
        segments=_to_segment_response(recording),
    )


def _to_segment_response(recording: Recording) -> list[RecordingSegmentResponse]:
    if recording.video is None or recording.stopped_at is None:
        return []
    return [
        RecordingSegmentResponse(
            index=0,
            target_id="active-tab",
            size_bytes=recording.video.size_bytes,
            format=recording.video.format,
            started_at=recording.started_at,
            stopped_at=recording.stopped_at,
        )
    ]
