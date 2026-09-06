from enum import StrEnum


class HealthStatus(StrEnum):
    """The worker's own view of whether it can serve traffic."""

    OK = "ok"
    NOT_READY = "not_ready"
