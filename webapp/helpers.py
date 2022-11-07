import math
from logging import getLogger

import requests

# import time
from .models import Instance

logger = getLogger(__name__)

# from .terraform import main as tf


def calculate_stop_time(timestamp_stop: int, amount: int) -> int:
    # time_now = time.time()
    hourly: int = 70
    hour: int = 60 * 60 * 1200
    return timestamp_stop + math.floor(amount / hourly) * hour


def action_wrapper(instance: Instance, action: str):
    pass
    # if hasattr(tf, action):
    #     fn = getattr(tf, action)
    #     fn(f"lnbits-{instance.id}", instance.domain)


def run_instance_action(instance: Instance, action: str) -> bool:
    if action == "restart":
        if instance.enabled:
            action_wrapper(instance, "disable")
        action_wrapper(instance, "enable")
    elif action == "disable" or action == "enable":
        if (
            not instance.enabled
            and action == "enable"
            or instance.enabled
            and action == "disabled"
        ):
            action_wrapper(instance, action)
    else:
        action_wrapper(instance, action)
    return True


def create_lnurlp(instance_id, config) -> str:
    url = f"{config['lnbits']['url']}/lnurlp/api/v1/links"
    price = config["lnbits"]["price"]
    api_key = config["lnbits"]["api_key"]
    webhook = config["webhook"]["url"]
    webhook_secret = config["webhook"]["secret"]
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Api-Key": api_key,
    }
    payload = {
        "description": f"top up for instance: {instance_id}",
        "min": price,
        "max": price * 10,
        "comment_chars": 0,
        "webhook_url": f"{webhook}/payment?api_key={webhook_secret}&instance_id={instance_id}",
        "success_text": "instance stop date extended, if it is your first payment, it will take 45-60 seconds until the admin url will be visible!",
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
    except:
        msg = "ERROR: trying to create lnurlp"
        logger.error(msg)
        raise Exception(msg)

    r = response.json()
    if response.status_code > 300:
        msg = f"ERROR: {r['detail']}"
        logger.error(msg)
        raise Exception(msg)

    return r["lnurl"]
