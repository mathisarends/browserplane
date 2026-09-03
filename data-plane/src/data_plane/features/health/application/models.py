from dataclasses import dataclass
from enum import StrEnum


class HealthStatus(StrEnum):
    OK = "ok"


@dataclass(frozen=True, slots=True)
class Health:
    """The worker's own view of whether it can serve traffic."""

    status: HealthStatus
