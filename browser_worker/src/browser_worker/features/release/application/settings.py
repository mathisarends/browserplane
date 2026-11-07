from pydantic import BaseModel, ConfigDict, Field


class ReleaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    recording_timeout: float = Field(default=5, gt=0)
    downloads_timeout: float = Field(default=5, gt=0)
    screencast_timeout: float = Field(default=5, gt=0)
    chromium_timeout: float = Field(default=10, gt=0)
    workspace_timeout: float = Field(default=4, gt=0)
    total_timeout: float = Field(default=20, gt=0)


class RestartSettings(BaseModel):
    """How this worker may hand itself back to whatever supervises it."""

    model_config = ConfigDict(frozen=True)

    # Ending the process only replaces the worker where something restarts it.
    # Without that promise the slot would be lost instead of recovered, so the
    # deployment has to opt in: a container restart policy, a pod, a supervisor.
    supervised: bool = False
    response_delay: float = Field(default=0.5, gt=0)
    shutdown_timeout: float = Field(default=15, gt=0)
