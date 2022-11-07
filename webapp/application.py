"""Application module."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import endpoints
from .containers import Container

def create_app() -> FastAPI:
    container = Container()

    db = container.db()
    db.create_database()

    app = FastAPI()
    app.container = container  # type: ignore

    login_manager = container.login_service().manager()
    login_manager.useRequest(app)

    app.include_router(endpoints.public_router)
    app.include_router(
        endpoints.router, dependencies=[Depends(login_manager)]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.config.cors(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
