from logging import getLogger
logger = getLogger(__name__)

from typing import List

from bcrypt import checkpw, gensalt, hashpw

from webapp.models import User, createUser
from webapp.repositories import UserRepository
from webapp.services.lnbits import LnbitsService


class UserService:
    def __init__(self, user_repository: UserRepository, lnbits_service: LnbitsService) -> None:
        self._repository: UserRepository = user_repository
        self._lnbits: LnbitsService = lnbits_service

    def get_users(self) -> List[User]:
        return self._repository.get_all()

    def get_user_by_id(self, user_id: int) -> User:
        return self._repository.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> User:
        return self._repository.get_by_email(email)

    def get_user_by_username(self, username: str) -> User:
        return self._repository.get_by_username(username)

    def login(self, username: str, password: str) -> User:
        pwd_bytes: bytes = password.encode("utf-8")
        user = self._repository.get_by_username(username)
        if not user or not checkpw(pwd_bytes, user.hashed_password):  # type: ignore
            raise
        return user

    def create_user(self, data: createUser) -> User:

        if self._repository.exists(data.username):
            raise Exception("user exists")

        pwd_bytes = data.password.encode("utf-8")
        salt = gensalt()
        password = hashpw(pwd_bytes, salt)

        usr, wallet_id, api_key = self._lnbits.create_user_and_wallet(data.username)
        lnurlp = self._lnbits.create_user_lnurlp(data.username, api_key, wallet_id)
        lnurlw = self._lnbits.create_user_lnurlw(data.username, api_key, wallet_id)
        tpos = self._lnbits.create_user_tpos(data.username, api_key)
        print("TPOS")
        print(tpos)

        user = User(
            username=data.username,
            hashed_password=password,
            is_active=True,
            usr=usr,
            wallet_id=wallet_id,
            api_key=api_key,
            lnurlp=lnurlp,
            lnurlw=lnurlw,
            tpos=tpos,
        )
        return self._repository.add(user)

    def delete_user_by_id(self, user_id: int) -> None:
        return self._repository.delete_by_id(user_id)
