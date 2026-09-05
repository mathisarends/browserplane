from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BrowserStateSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_STATE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    restore_timeout: float = Field(default=10, gt=0)
    max_tabs: int = Field(default=20, gt=0)
