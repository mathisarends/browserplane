from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkspaceSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WORKSPACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    path: Path = Path("workspace")
