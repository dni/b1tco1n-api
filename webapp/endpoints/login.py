from fastapi import APIRouter, Depends, status, Response

from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import Response, JSONResponse

from dependency_injector.wiring import Provide, inject

from webapp.services.user import UserService
from webapp.services.login import LoginService
from webapp.models import createUser
from webapp.containers import Container


login_router = APIRouter()

# the python-multipart package is required to use the OAuth2PasswordRequestForm
@login_router.post("/login")
@inject
async def login_endpoint(
    response: Response,
    data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(Provide[Container.user_service]),
    login_service: LoginService = Depends(Provide[Container.login_service]),
):
    try:
        user = user_service.login(data.username, data.password)
        if user:
            access_token = login_service.create_access_token(data=dict(sub=user.username))
            login_service.set_cookie(response, access_token)
            return {"access_token": access_token, "token_type": "bearer"}
    except:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

@login_router.get("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status":"success"}

@login_router.post("/signup")
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
