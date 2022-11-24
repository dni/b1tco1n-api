from fastapi import APIRouter, Depends, status, Response, Request, BackgroundTasks, Query, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from dependency_injector.wiring import Provide, inject
from webapp.services.instance import InstanceService
from webapp.models import updateAdmin
from webapp.containers import Container

api_key_header = APIKeyHeader(
    name="X-API-KEY",
    auto_error=False,
)

api_key_query = APIKeyQuery(
    name="api_key",
    auto_error=False,
)

webhook_router = APIRouter()

# # route for lnbits instances to call back and set admin user
@webhook_router.post("/webhook/saas")
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


# # route for lnurlp webhook on success
@webhook_router.post("/webhook/payment")
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

    print(amount)
    print(tasks)
    # payment = updatePayment(amount=amount, instance_id=instance_id)
    # tasks.add_task(instance_service.update_instance_payment, payment)
    # await instance_service.update_instance_payment(payment)


