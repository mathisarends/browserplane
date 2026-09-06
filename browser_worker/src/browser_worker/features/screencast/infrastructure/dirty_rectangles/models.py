from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

type RgbFrame = npt.NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class EncodingMetrics:
    """How long one update took, and how much of the canvas it carried."""

    decode_ms: float
    diff_ms: float
    encode_ms: float
    dirty_ratio: float
    patches: int


@dataclass(frozen=True, slots=True)
class EncodedUpdate:
    packet: bytes
    metrics: EncodingMetrics
