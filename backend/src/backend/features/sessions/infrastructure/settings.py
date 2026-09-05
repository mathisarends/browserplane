from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SessionSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    suspended_session_ttl_seconds: int = Field(default=86_400, gt=0)
    browser_width: int = Field(default=1600, gt=0)
    browser_height: int = Field(default=900, gt=0)
