from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LeaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_LEASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    heartbeat_interval_seconds: int = Field(default=10, gt=0)
    ttl_seconds: int = Field(default=30, gt=0)
    grace_period_seconds: int = Field(default=45, ge=0)
    reaper_interval_seconds: int = Field(default=5, gt=0)
    reaper_batch_size: int = Field(default=20, gt=0, le=500)
    cleanup_retry_seconds: int = Field(default=5, gt=0)
