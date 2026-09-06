from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScreencastSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCREENCAST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    quality: int = Field(default=80, ge=0, le=100)


class DirtyRectangleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIRTY_RECTANGLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    tile_width: int = Field(default=128, gt=0, le=65535)
    tile_height: int = Field(default=128, gt=0, le=65535)
    jpeg_quality: int = Field(default=80, ge=0, le=100)
