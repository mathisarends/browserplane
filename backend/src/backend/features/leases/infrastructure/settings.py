from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.features.leases.application import LeaseSettings


class EnvironmentLeaseSettings(LeaseSettings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_LEASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )
