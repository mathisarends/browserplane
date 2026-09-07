from collections.abc import Sequence
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class BrowserPoolSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_BROWSER_POOL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    worker_urls: Annotated[tuple[str, ...], NoDecode] = (
        "http://127.0.0.1:8011",
        "http://127.0.0.1:8012",
    )

    @field_validator("worker_urls", mode="before")
    @classmethod
    def _split(cls, value: object) -> object:
        """Accept a comma-separated list, so adding a worker is one env var."""
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @field_validator("worker_urls", mode="after")
    @classmethod
    def _reject_duplicates(cls, value: Sequence[str]) -> Sequence[str]:
        # The URL is a worker's identity, so a repeat would collapse two slots.
        if len(set(value)) != len(value):
            raise ValueError("browser worker urls must be unique")
        return value
