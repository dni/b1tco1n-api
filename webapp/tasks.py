import asyncio
import logging
import time

from .models import Instance

logger: logging.Logger = logging.getLogger("uvicorn")


async def check_instances(instance_service, destroy_time: int, sleep_time: int) -> None:
    while True:
        instances: list[Instance] = instance_service.get_instances_for_check()
        for instance in instances:
            if instance.enabled and instance.timestamp_stop <= int(time.time()):
                instance_service.update_instance_action(instance.instance_id, "disable")
                logger.info(f"disabled instance: {instance.instance_id}.")
            if int(time.time()) - instance.timestamp_stop >= destroy_time:
                instance_service.update_instance_action(instance.instance_id, "destroy")
                logger.info(f"destroyed instance: {instance.instance_id}.")

        logger.info(f"ran periodic check, checked {len(instances)} instances.")
        # run every 15 min
        await asyncio.sleep(sleep_time)
