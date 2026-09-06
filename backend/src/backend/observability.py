import logging
from copy import deepcopy
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from uvicorn.config import LOGGING_CONFIG

FORMAT = "%(levelname)s:%(name)s:%(message)s"


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


def uvicorn_log_config(settings: LoggingSettings | None = None) -> dict[str, Any]:
    """Uvicorn's own config, extended with a handler for backend loggers."""
    settings = settings or LoggingSettings()
    config = deepcopy(LOGGING_CONFIG)
    config["formatters"]["backend"] = {"format": FORMAT}
    config["handlers"]["backend"] = {
        "class": "logging.StreamHandler",
        "formatter": "backend",
        "stream": "ext://sys.stderr",
    }
    config["loggers"]["backend"] = {
        "handlers": ["backend"],
        "level": settings.log_level,
        "propagate": False,
    }
    return config


def configure_logging(settings: LoggingSettings | None = None) -> None:
    """Configure logging for a process that does not run under uvicorn."""
    settings = settings or LoggingSettings()
    logging.basicConfig(level=settings.log_level, format=FORMAT)
