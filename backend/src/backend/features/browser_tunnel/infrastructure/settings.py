from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BrowserSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
    )

    cdp_url: str
    width: int = Field(default=1600, gt=0)
    height: int = Field(default=900, gt=0)


class BrowserTunnelSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    browser_width: int = Field(default=1600, gt=0)
    browser_height: int = Field(default=900, gt=0)
