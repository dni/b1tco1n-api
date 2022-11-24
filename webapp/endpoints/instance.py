from fastapi import APIRouter, Depends, status, Response, Request, BackgroundTasks, Query

from dependency_injector.wiring import Provide, inject

from webapp.services.instance import InstanceService
from webapp.models import runInstanceAction
from webapp.helpers import create_lnurlp

from webapp.containers import Container

instance_router = APIRouter()

@instance_router.post("/instance")
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


@instance_router.get("/instance")
@inject
def get_list(
    req: Request,
    instance_service: InstanceService = Depends(Provide[Container.instance_service]),
):
    user = req.state.user
    return instance_service.get_instances_by_user_id(user.id)


actions: list[str] = ["enable", "disable", "reset", "restart", "destroy"]


@instance_router.put("/instance")
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
