from data_plane.features.recordings.application.models import (
    RecordedSegment,
    Recording,
)
from data_plane.features.recordings.presentation.schemas import (
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
        segments=[_to_segment_response(segment) for segment in recording.segments],
    )


def _to_segment_response(segment: RecordedSegment) -> RecordingSegmentResponse:
    return RecordingSegmentResponse(
        index=segment.index,
        target_id=segment.target_id,
        size_bytes=segment.size_bytes,
        format=segment.format,
        started_at=segment.started_at,
        stopped_at=segment.stopped_at,
    )
