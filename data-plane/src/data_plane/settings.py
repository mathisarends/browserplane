from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataPlaneSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATA_PLANE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    executable: str | None = None
    headless: bool = True
    width: int = Field(default=1600, gt=0)
    height: int = Field(default=900, gt=0)
    screencast_quality: int = Field(default=80, ge=0, le=100)
    recording_frame_rate: int = Field(default=30, gt=0)
    recording_audio: bool = False
    recording_start_timeout: float = Field(default=10, gt=0)
    startup_timeout: float = Field(default=15, gt=0)
    public_base_url: str = "ws://127.0.0.1:8000"
