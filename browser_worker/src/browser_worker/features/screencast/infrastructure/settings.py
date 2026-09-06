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

    # Everything downstream is bounded by this: the dirty rectangle stream
    # re-encodes what the capture delivered, so its patches can never be
    # sharper than the frame they were cut from.
    quality: int = Field(default=85, ge=0, le=100)


class DirtyRectangleSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DIRTY_RECTANGLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # Small tiles keep the cheap edits cheap - a caret, a hover state, a
    # cursor - and neighbouring dirty tiles are merged back into larger
    # rectangles before encoding, so the finer grid costs no extra JPEGs.
    tile_width: int = Field(default=64, gt=0, le=65535)
    tile_height: int = Field(default=64, gt=0, le=65535)
    # Patches are re-encoded from an already lossy capture, so they are kept
    # above the capture quality: the second pass then adds little of its own.
    jpeg_quality: int = Field(default=88, ge=0, le=100)
    # 0 is 4:4:4. Chroma subsampling smears the thin, high-contrast edges that
    # a browser canvas is made of, and it does so per patch, which would leave
    # seams where a patch meets pixels encoded in an earlier update.
    jpeg_subsampling: int = Field(default=0, ge=0, le=2)
    # Huffman tables tuned per patch, at the cost of a second encoding pass.
    optimize_jpeg: bool = True
