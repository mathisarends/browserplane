from pydantic_settings import BaseSettings, SettingsConfigDict


class BucketSettings(BaseSettings):
    """Connection settings for an optional S3-compatible bucket."""

    model_config = SettingsConfigDict(
        env_prefix="BUCKET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    name: str | None = None
    endpoint: str | None = None
    prefix: str = ""
