"""Containers module."""

# import sys
# import logging
from dependency_injector import containers, providers

from .database import Database
from .repositories import InstanceRepository, UserRepository
from .services.user import UserService
from .services.login import LoginService
from .services.lnbits import LnbitsService
from .services.websocket import WebSocketService
from .services.sse import SSEService
from .services.instance import InstanceService

class Container(containers.DeclarativeContainer):

    wiring_config = containers.WiringConfiguration(modules=[".endpoints"])

    config = providers.Configuration(yaml_files=["config.yml"])

    db = providers.Singleton(Database, db_url=config.db.url)

    # logging = providers.Resource(
    #     logging.basicConfig,
    #     stream=sys.stdout,
    #     level=config.log.level,
    #     format=config.log.format,
    # )

    lnbits_service = providers.Factory(
        LnbitsService,
        config=config,
    )

    user_repository = providers.Factory(
        UserRepository,
        session_factory=db.provided.session,
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        lnbits_service=lnbits_service,
    )

    instance_repository = providers.Factory(
        InstanceRepository,
        session_factory=db.provided.session,
    )

    instance_service = providers.Factory(
        InstanceService,
        instance_repository=instance_repository,
    )

    login_service = providers.Factory(
        LoginService,
        secret=config.db.secret,
        user_service=user_service,
    )

    websocket_service = providers.Factory(
        WebSocketService,
        login_service=login_service,
        lnbits_service=lnbits_service,
    )

    sse_service = providers.Factory(
        SSEService,
    )
