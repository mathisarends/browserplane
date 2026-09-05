from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RecordingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RECORDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    frame_rate: int = Field(default=30, gt=0)
    audio: bool = False
    start_timeout: float = Field(default=10, gt=0)
