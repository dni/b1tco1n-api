"""Repositories module."""

from contextlib import AbstractContextManager
from typing import Callable, List

from sqlalchemy.orm import Session

from .models import User


class UserRepository:
    def __init__(
        self, session_factory: Callable[..., AbstractContextManager[Session]]
    ) -> None:
        self.session_factory = session_factory

    def get_all(self) -> List[User]:
        with self.session_factory() as session:
            return session.query(User).all()

    def get_by_id(self, user_id: int) -> User:
        with self.session_factory() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise UserNotFoundError(user_id)
            return user

    def get_by_email(self, email: str) -> User:
        with self.session_factory() as session:
            user = session.query(User).filter(User.email == email).first()
            if not user:
                raise UserNotFoundError(email)
            return user

    def get_by_username(self, username: str) -> User:
        with self.session_factory() as session:
            query = session.query(User)
            user = query.filter(User.username == username).first()
            if not user:
                raise UserNotFoundError(username)
            return user

    def exists(self, username: str) -> bool:
        with self.session_factory() as session:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                return False
            return True

    def add(self, user: User) -> User:
        with self.session_factory() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def delete_by_id(self, user_id: int) -> None:
        with self.session_factory() as session:
            entity: User = session.query(User).filter(User.id == user_id).first()  # type: ignore
            if not entity:
                raise UserNotFoundError(user_id)
            session.delete(entity)
            session.commit()


class NotFoundError(Exception):
    entity_name: str

    def __init__(self, entity_id):
        super().__init__(f"{self.entity_name} not found, id: {entity_id}")


class UserNotFoundError(NotFoundError):
    entity_name: str = "User"
