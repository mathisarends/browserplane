from pydantic_settings import BaseSettings, SettingsConfigDict


class BucketCredentials(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BUCKET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    access_key: str | None = None
    secret_key: str | None = None
