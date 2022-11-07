from logging import getLogger
logger = getLogger(__name__)

from time import time
from random_username.generate import generate_username
from starlette.concurrency import run_in_threadpool

from webapp.helpers import calculate_stop_time, run_instance_action
from webapp.models import Instance, runInstanceAction, updateAdmin, updatePayment

from webapp.repositories import InstanceRepository


class InstanceService:
    def __init__(self, instance_repository: InstanceRepository) -> None:
        self._repository: InstanceRepository = instance_repository

    def get_instances_by_user_id(self, user_id: int) -> list[Instance]:
        return self._repository.get_by_user_id(user_id)

    def get_instance(self, instance_id: int) -> Instance:
        return self._repository.get_by_id(instance_id)

    def delete_instance(self, instance_id: int) -> None:
        return self._repository.delete_by_id(instance_id)

    def create_instance(self, user_id) -> Instance:
        instance = Instance(
            domain=generate_username().pop().lower() + ".dev.lnbits.com",
            user_id=user_id,
            timestamp=int(time()),
            timestamp_stop=int(time()),
        )
        return self._repository.add(instance)

    def update_instance_lnurl(self, instance_id: int, lnurl: str) -> Instance:
        return self._repository.update(instance_id, {"lnurl": lnurl})

    async def update_instance_action(self, data: runInstanceAction) -> None:
        # run terraform actions
        instance = self.get_instance(data.instance_id)
        if data.action == "deploy":
            self._repository.update(
                data.instance_id, {"is_active": True, "is_enabled": True}
            )
        if data.action == "enable":
            self._repository.update(data.instance_id, {"is_enabled": True})
        if data.action == "disable":
            self._repository.update(data.instance_id, {"is_enabled": False})
        if data.action == "destroy":
            self.delete_instance(data.instance_id)
        await run_in_threadpool(run_instance_action, instance, data.action)

    def update_instance_admin(self, data: updateAdmin) -> None:
        try:
            instance_id = int(data.instance_id.replace("lnbits-", ""))
            self._repository.update(instance_id, {"adminuser": data.adminuser})
        except:
            logger.error("update_instance_admin failed. unexpected instance_id")

    async def update_instance_payment(self, data: updatePayment) -> None:
        instance = self.get_instance(data.instance_id)
        timestamp_stop = calculate_stop_time(instance.timestamp_stop, data.amount)
        self._repository.update(data.instance_id, {"timestamp_stop": timestamp_stop})

        action = None

        # first time start
        if not instance.is_active:
            action = "deploy"
        # enabled it even if it enabled
        elif not instance.is_enabled:
            action = "enable"

        if action:
            await self.update_instance_action(
                runInstanceAction(
                    instance_id=data.instance_id,
                    action=str(action),
                )
            )
