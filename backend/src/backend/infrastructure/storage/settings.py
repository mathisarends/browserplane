from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseSettings):
    """Connection settings for an optional S3-compatible object store."""

    model_config = SettingsConfigDict(
        env_prefix="STORAGE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    bucket: str | None = None
    endpoint: str | None = None
    region: str = "us-east-1"
    prefix: str = ""
