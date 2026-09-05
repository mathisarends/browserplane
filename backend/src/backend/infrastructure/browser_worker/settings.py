from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BrowserWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_BROWSER_WORKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    request_timeout_seconds: float = Field(default=30, gt=0)
    transfer_timeout_seconds: float = Field(default=3600, gt=0)
