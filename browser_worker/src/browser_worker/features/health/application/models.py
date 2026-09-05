from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class Health:
    """The worker's own view of whether it can serve traffic."""

    status: HealthStatus
