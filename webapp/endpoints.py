"""Endpoints module."""

import asyncio
from logging import getLogger

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status, WebSocket, WebSocketDisconnect, Cookie
from fastapi.params import Security
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from starlette.responses import Response, JSONResponse

# from .application import app
from .containers import Container
from .helpers import create_lnurlp
from .models import (createUser, runInstanceAction, updateAdmin, updatePayment)

from .services.instance import InstanceService
from .services.user import UserService
from .services.login import LoginService
from .services.websocket import WebSocketService
from .services.sse import SSEService

logger = getLogger("uvicorn")

public_router = APIRouter()
router = APIRouter()

# the python-multipart package is required to use the OAuth2PasswordRequestForm
@public_router.post("/login")
@inject
async def login_endpoint(
    response: Response,
    data: OAuth2PasswordRequestForm = Depends(),
    login_service: LoginService = Depends(Provide[Container.login_service]),
    user_service: UserService = Depends(Provide[Container.user_service]),
):
    try:
        user = user_service.login(data.username, data.password)
        if user:
            access_token = login_service.create_access_token(data=dict(sub=user.username))
            login_service.set_cookie(response, access_token)
            return {"access_token": access_token, "token_type": "bearer"}
    except:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

@public_router.get("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status":"success"}

@public_router.post("/signup")
@inject
async def signup_endpoint(
    data: createUser,
    response: Response,
    user_service: UserService = Depends(Provide[Container.user_service]),
    login_service: LoginService = Depends(Provide[Container.login_service]),
) -> dict[str, str] | Response:
    if (data.password != data.password_repeat):
        error_json = {"detail": [{
            "loc": ["body", "password_repeat"],
            "msg": "passwords do not match",
        }]}
        return JSONResponse(error_json, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    try:
        user = user_service.create_user(data)
        access_token = login_service.create_access_token(data=dict(sub=user.username))
        login_service.set_cookie(response, access_token)
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as exc:
        return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


@router.get("/user")
async def user_endpoint(
    req: Request
):
    user = req.state.user
    return user

@router.websocket("/ws")
@inject
async def websocket_endpoint(
    websocket: WebSocket,
    access_token: str = Cookie(default=None),
    websocket_service: WebSocketService = Depends(Provide[Container.websocket_service]),
    login_service: LoginService = Depends(Provide[Container.login_service]),
    sse_service: SSEService = Depends(Provide[Container.sse_service]),
    config=Depends(Provide[Container.config]),
):
    if not access_token:
        return await websocket.close()

    # check if access token is still valid
    try:
        user = await login_service.user(access_token)
    except:
        return await websocket.close()

    sse_url = f"{config['lnbits']['url']}/api/v1/payments/sse?api-key={user.api_key}"
    await websocket.accept()
    try:
        await asyncio.gather(
            websocket_service.start_listener(websocket, access_token),
            sse_service.start_listener(websocket, sse_url),
            return_exceptions=True
        )
    except asyncio.exceptions.CancelledError:
        await websocket_service.cancel_listener()
        sse_service.cancel_listener()
    except WebSocketDisconnect:
        await websocket_service.cancel_listener()
        sse_service.cancel_listener()



@router.post("/instance")
@inject
def create_instance_endpoint(
    req: Request,
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
    config=Depends(Provide[Container.config]),
):
    user = req.state.user
    instance = instance_service.create_instance(user.id)
    try:
        lnurl = create_lnurlp(instance.id, config)
        instance = instance_service.update_instance_lnurl(instance.id, lnurl)
        return instance
    except Exception as exc:
        logger.error(exc)
        return Response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)


@router.get("/instance")
@inject
def get_list(
    req: Request,
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
):
    user = req.state.user
    return instance_service.get_instances_by_user_id(user.id)


actions: list[str] = ["enable", "disable", "reset", "restart", "destroy"]


@router.put("/instance")
@inject
def lnbits_api_update_instance(
    req: Request,
    data: runInstanceAction,
    tasks: BackgroundTasks,
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
):

    if data.action not in actions:
        return Response("invalid action", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        instance = instance_service.get_instance(data.instance_id)
    except:
        return Response(
            "instance does not exist", status_code=status.HTTP_401_UNAUTHORIZED
        )

    user = req.state.user
    if user.id != instance.user_id:
        return Response("not your instance", status_code=status.HTTP_401_UNAUTHORIZED)

    tasks.add_task(instance_service.update_instance_action, data)
    # instance_service.update_instance_action(data)
    return {"message": f"ran action {data.action}"}


api_key_header = APIKeyHeader(
    name="X-API-KEY",
    auto_error=False,
)

# # route for lnbits instances to call back and set admin user
@public_router.post("/instance/admin")
@inject
async def lnbits_api_update_admin(
    data: updateAdmin,
    api_key_header: str = Security(api_key_header),  # type: ignore
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
    config=Depends(Provide[Container.config]),
):
    if config["webhook"]["secret"] != api_key_header:
        return Response("unauthorzied", status_code=status.HTTP_401_UNAUTHORIZED)
    return instance_service.update_instance_admin(data)


api_key_query = APIKeyQuery(
    name="api_key",
    auto_error=False,
)

# # route for lnurlp webhook on success
@public_router.post("/webhook/payment")
@inject
async def lnbits_api_invoice_paid(
    request: Request,
    tasks: BackgroundTasks,
    instance_id: int = Query(...),
    api_key_query: str = Security(api_key_query),  # type: ignore
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
    config=Depends(Provide[Container.config]),
):

    if config["webhook"]["secret"] != api_key_query:
        return Response("unauthorized", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        instance_service.get_instance(instance_id)
    except:
        return Response("instance not found", status_code=status.HTTP_401_UNAUTHORIZED)

    json = await request.json()
    amount = int(json["amount"] / 1000)

    payment = updatePayment(amount=amount, instance_id=instance_id)
    tasks.add_task(instance_service.update_instance_payment, payment)
    # await instance_service.update_instance_payment(payment)


@public_router.get("/")
def get_status():
    return {"status": "OK"}
