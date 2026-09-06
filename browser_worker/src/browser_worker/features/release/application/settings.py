from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReleaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_WORKER_RELEASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    recording_timeout: float = Field(default=5, gt=0)
    downloads_timeout: float = Field(default=5, gt=0)
    screencast_timeout: float = Field(default=5, gt=0)
    chromium_timeout: float = Field(default=10, gt=0)
    workspace_timeout: float = Field(default=4, gt=0)
    total_timeout: float = Field(default=20, gt=0)
