import os

import uvicorn

from backend.observability import LoggingSettings, uvicorn_log_config


def main() -> None:
    settings = LoggingSettings()
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=bool(os.getenv("RELOAD")),
        log_config=uvicorn_log_config(settings),
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
