import uvicorn

from .application import create_app


def start():
    app = create_app()
    config = uvicorn.Config(
        app,
        host=app.container.config.uvicorn.host(),
        port=app.container.config.uvicorn.port(),
        forwarded_allow_ips="*"
    )
    server = uvicorn.Server(config)
    server.run()
