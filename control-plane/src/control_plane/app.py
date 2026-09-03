from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from control_plane.lifespan import lifespan
from control_plane.provider import ControlPlaneProvider
from control_plane.provisioning import BrowserProvisioner
from control_plane.routes import router


def create_app(provisioner: BrowserProvisioner | None = None) -> FastAPI:
    app = FastAPI(title="Browser Control Plane", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    setup_dishka(make_async_container(ControlPlaneProvider(provisioner)), app)
    return app


app = create_app()
