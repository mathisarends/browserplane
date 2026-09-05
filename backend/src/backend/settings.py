from uuid import UUID

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.features.browsers.application.models import BrowserSlot


class BackendSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    database_url: str = "postgresql+asyncpg://browser:browser@127.0.0.1:5432/browser"

    # A suspended session costs a row, not a browser, so it may wait for a
    # human far longer than a lease on a running browser ever should.
    suspended_session_ttl_seconds: int = 86_400
    browser_width: int = 1600
    browser_height: int = 900

    browser_worker_1_url: str = "http://127.0.0.1:8011"
    browser_worker_2_url: str = "http://127.0.0.1:8012"

    def slots(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(
                UUID("00000000-0000-0000-0000-000000000001"),
                self.browser_worker_1_url,
            ),
            BrowserSlot(
                UUID("00000000-0000-0000-0000-000000000002"),
                self.browser_worker_2_url,
            ),
        )
