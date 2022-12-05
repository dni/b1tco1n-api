import asyncio
from logging import getLogger

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Cookie

# from .application import app
from webapp.containers import Container
from webapp.services.login import LoginService
from webapp.services.websocket import WebSocketService
from webapp.services.sse import SSEService

logger = getLogger("uvicorn")

websocket_router = APIRouter()

@websocket_router.websocket("/ws")
@inject
async def websocket_endpoint(
    websocket: WebSocket,
    access_token: str = Cookie(default=None),
    websocket_service: WebSocketService = Depends(Provide[Container.websocket_service]),
    login_service: LoginService = Depends(Provide[Container.login_service]),
    sse_service: SSEService = Depends(Provide[Container.sse_service]),
    url=Depends(Provide[Container.config.lnbits.url]),
):
    if not access_token:
        return await websocket.close()

    # check if access token is still valid
    try:
        user = await login_service.user(access_token)
    except:
        return await websocket.close()

    sse_url = f"{url}/api/v1/payments/sse?api-key={user.api_key}"
    await websocket.accept()
    try:
        tasks = await asyncio.gather(
            websocket_service.start_listener(websocket, access_token),
            sse_service.start_listener(websocket, sse_url)
        )
        # gather catched first exception, cancel all
        print("gathered all tasks")
        print(tasks)
        for task in tasks:
            if task:
                task.cancel()
        print("canceled all tasks")
    except WebSocketDisconnect:
        print("websocket disconnect")
    except asyncio.exceptions.CancelledError:
        print("canceled error")
        await websocket_service.cancel_listener()
        sse_service.cancel_listener()
    except Exception as exc:
        print(str(exc))
        print("unhandled exception")
