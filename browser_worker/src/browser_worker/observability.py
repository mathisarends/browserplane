from copy import deepcopy
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict
from uvicorn.config import LOGGING_CONFIG

FORMAT = "%(levelname)s:%(name)s:%(message)s"


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BROWSER_WORKER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


def uvicorn_log_config(settings: LoggingSettings | None = None) -> dict[str, Any]:
    """Uvicorn's own config, extended with a handler for worker loggers."""
    settings = settings or LoggingSettings()
    config = deepcopy(LOGGING_CONFIG)
    config["formatters"]["browser_worker"] = {"format": FORMAT}
    config["handlers"]["browser_worker"] = {
        "class": "logging.StreamHandler",
        "formatter": "browser_worker",
        "stream": "ext://sys.stderr",
    }
    config["loggers"]["browser_worker"] = {
        "handlers": ["browser_worker"],
        "level": settings.log_level,
        "propagate": False,
    }
    return config
