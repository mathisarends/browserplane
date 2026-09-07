from collections.abc import AsyncGenerator

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.application.models import RecordingFormat

_WEBM_SIGNATURE = b"\x1a\x45\xdf\xa3"
_MP4_SIGNATURE = b"ftyp"
_SIGNATURE_BYTES = 12


async def read_signature(chunks: AsyncGenerator[bytes]) -> bytes:
    """Collect enough leading bytes of a video to recognise its container."""
    signature = bytearray()
    async for chunk in chunks:
        signature += chunk
        if len(signature) >= _SIGNATURE_BYTES:
            break
    if not signature:
        raise RecordingFailedException("Browser returned an empty recording")
    return bytes(signature)


def container_format(signature: bytes) -> RecordingFormat:
    """Name the container the browser chose for this recording."""
    if signature.startswith(_WEBM_SIGNATURE):
        return RecordingFormat.WEBM
    if signature[4:8] == _MP4_SIGNATURE:
        return RecordingFormat.MP4
    raise RecordingFailedException("Browser returned an unknown video container")
