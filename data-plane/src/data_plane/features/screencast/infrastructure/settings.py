from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScreencastSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCREENCAST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    quality: int = Field(default=80, ge=0, le=100)
