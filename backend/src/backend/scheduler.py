"""Run with python -m backend.scheduler, independently of the HTTP API."""
import asyncio
import logging

from backend.app import FEATURES
from backend.container import create_container
from backend.features.browser_requests.infrastructure.dispatcher import Dispatcher
from backend.features.browser_requests.infrastructure.notifications import PostgresListener


async def main():
    container = create_container(FEATURES)
    try:
        listener = await container.get(PostgresListener)
        dispatcher = await container.get(Dispatcher)
        async with listener.running():
            await dispatcher.run()
    finally:
        await container.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
