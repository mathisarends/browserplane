from dataclasses import dataclass

from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class BrowserSlot:
    id: str
    tunnel_url: str


class ControlPlaneSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONTROL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    browser_1_tunnel_url: str = "ws://127.0.0.1:8001/api/browser/ws"
    browser_2_tunnel_url: str = "ws://127.0.0.1:8002/api/browser/ws"

    def slots(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot("browser-1", self.browser_1_tunnel_url),
            BrowserSlot("browser-2", self.browser_2_tunnel_url),
        )
