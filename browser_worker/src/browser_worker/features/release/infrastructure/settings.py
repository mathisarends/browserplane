from pydantic_settings import BaseSettings, SettingsConfigDict

from browser_worker.features.release.application import ReleaseSettings, RestartSettings


class EnvironmentReleaseSettings(ReleaseSettings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_WORKER_RELEASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )


class EnvironmentRestartSettings(RestartSettings, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_WORKER_RESTART_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )
