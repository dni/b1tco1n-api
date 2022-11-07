from fastapi_login import LoginManager
from webapp.models import User
from webapp.services.user import UserService


class LoginService:
    def __init__(self, secret: str, user_service: UserService) -> None:
        self._manager = LoginManager(secret, token_url="/auth/token", use_cookie=True, cookie_name="access_token")

        @self._manager.user_loader()  # type: ignore
        async def load_user(username: str):
            return user_service.get_user_by_username(username)

    def manager(self) -> LoginManager:
        return self._manager

    async def user(self, token) -> User:
        return await self._manager.get_current_user(token)

    def create_access_token(self, **kwargs) -> str:
        return self._manager.create_access_token(**kwargs)

    def set_cookie(self, response, token: str) -> None:
        self._manager.set_cookie(response, token) # httponly=True ?!
        # response.set_cookie(key="access_token", value=token, httponly=True)
