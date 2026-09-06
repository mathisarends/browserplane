from pydantic import Field, SecretStr
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
    authentication_state_encryption_key: SecretStr = Field(min_length=1)
