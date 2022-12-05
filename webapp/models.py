"""Models module."""

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String
from .database import Base


class createUser(BaseModel):
    username: str = Query(default=..., min_length=3, max_length=50, regex="^\\w+$")
    password: str = Query(default=..., min_length=8, max_length=50)
    password_repeat: str = Query(default=..., min_length=8, max_length=50)


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    # email = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    usr = Column(String)
    wallet_id = Column(String)
    api_key = Column(String)

    lnurlp = Column(String)
    lnurlw = Column(String)
    tpos = Column(String)

    def __repr__(self):
        return (
            f"<User(id={self.id}, "
            f'username="{self.username}", '
            f'hashed_password="{self.hashed_password}", '
            f'usr="{self.usr}", '
            f'wallet_id="{self.wallet_id}", '
            f'api_key="{self.api_key}", '
            f'lnurlp="{self.lnurlp}", '
            f'lnurlw="{self.lnurlw}", '
            f'tpos="{self.tpos}", '
            f"is_active={self.is_active})>"
        )
