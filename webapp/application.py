"""Application module."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import (
        login,
        websocket,
        status,
        webhook,
        instance,
)

from .containers import Container

def include_routes(app, login_manager):
    # public paths
    app.include_router(login.login_router)
    app.include_router(status.status_router)
    # websocket auth
    app.include_router(websocket.websocket_router)
    # get vars auth for webhooks
    app.include_router(webhook.webhook_router)
    # private
    app.include_router(instance.instance_router, dependencies=[Depends(login_manager)])


def create_app() -> FastAPI:
    container = Container()

    db = container.db()
    db.create_database()

    app = FastAPI()
    app.container = container  # type: ignore

    login_manager = container.login_service().manager()
    login_manager.useRequest(app)

    include_routes(app, login_manager)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.config.cors(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
