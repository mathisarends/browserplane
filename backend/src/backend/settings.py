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

    browser_1_data_plane_url: str = "http://127.0.0.1:8011"
    browser_1_tunnel_url: str = "ws://127.0.0.1:8021/api/v1/browser/ws"
    browser_1_screencast_url: str = (
        "ws://127.0.0.1:8011/api/v1/browser/"
        "00000000-0000-0000-0000-000000000001/screencast"
    )
    browser_2_data_plane_url: str = "http://127.0.0.1:8012"
    browser_2_tunnel_url: str = "ws://127.0.0.1:8022/api/v1/browser/ws"
    browser_2_screencast_url: str = (
        "ws://127.0.0.1:8012/api/v1/browser/"
        "00000000-0000-0000-0000-000000000002/screencast"
    )

    def slots(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(
                UUID("00000000-0000-0000-0000-000000000001"),
                self.browser_1_data_plane_url,
                self.browser_1_tunnel_url,
                self.browser_1_screencast_url,
            ),
            BrowserSlot(
                UUID("00000000-0000-0000-0000-000000000002"),
                self.browser_2_data_plane_url,
                self.browser_2_tunnel_url,
                self.browser_2_screencast_url,
            ),
        )
