import requests

from typing import Tuple

from logging import getLogger
logger = getLogger(__name__)


class LnbitsService:

    def __init__(self, config) -> None:
        self._config = config

    def request(self, url, method="post", payload=None, api_key=None):
        url = f"{self._config['lnbits']['url']}{url}"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Api-Key": api_key,
        }
        if hasattr(requests, method):
            fn = getattr(requests, method)
            try:
                response = fn(url, headers=headers, json=payload)
            except Exception as exc:
                msg = f"ERROR: making lnbits request. {exc}"
                logger.error(msg)
                raise Exception(msg)
        else:
            print("else")
            msg = f"ERROR: trying to make a weird request. {method}"
            logger.error(msg)
            raise Exception(msg)

        json = response.json()
        if response.status_code > 300:
            msg = f"ERROR: {json['detail']}"
            logger.error(msg)
            raise Exception(msg)
        return json

    def create_invoice(self, api_key: str, amount: int, description: str = "withdraw"):
        data = self.request("/api/v1/payments", api_key=api_key, method="post", payload={
            "amount": amount,
            "memo": description,
            "unit": "sat",
            "out": False,
        })
        return data.get("payment_hash"), data.get("payment_request")

    def send_withdraw(self, callback, k1, payment_request):
        try:
            url = f"{callback}?k1={k1}&pr={payment_request}"
            response = requests.get(url)
        except Exception as exc:
            msg = str(exc)
            logger.error(msg)
            raise Exception(msg)
        json = response.json()
        if response.status_code > 300:
            msg = f"{json['detail']}"
            logger.error(msg)
            raise Exception(msg)

        successMessage = ""
        if json.get("successAction"):
            successMessage = json.get("successAction").get("message")

        return json.get("pr"), successMessage

    def decode_invoice(self, invoice: str):
        data = self.request("/api/v1/payments/decode", payload={"data": invoice})
        return data

    def get_lnurl_invoice(self, callback: str, amount: int, comment: str | None) -> tuple[str, str]:
        try:
            url = f"{callback}?amount={amount}"
            response = requests.get(url)
        except Exception as exc:
            msg = f"ERROR: making lnurl invoice request. {exc}"
            logger.error(msg)
            raise Exception(msg)
        json = response.json()
        if response.status_code > 300:
            msg = f"ERROR: making lnurl invoice request. {json['detail']}"
            logger.error(msg)
            raise Exception(msg)
        return json.get("pr"), json.get("successAction").get("message")

    def decode_lnurl(self, domain: str):
        try:
            response = requests.get(domain)
        except Exception as exc:
            msg = f"ERROR: making lnurl request. {exc}"
            logger.error(msg)
            raise Exception(msg)
        json = response.json()
        if response.status_code > 300:
            msg = f"ERROR: making lnurl request. {json['detail']}"
            logger.error(msg)
            raise Exception(msg)
        return json


    def get_payments(self, api_key: str):
        data = self.request("/api/v1/payments", method="get", api_key=api_key)
        return data

    def get_balance(self, api_key: str) -> int:
        data = self.request("/api/v1/wallet", method="get", api_key=api_key)
        balance = 0
        if data:
            balance = data.get("balance") / 1000
        return balance

    def create_user_and_wallet(self, username) -> Tuple:
        api_key = self._config['lnbits']['api_key']
        admin_key = self._config['lnbits']['admin_key']
        json = self.request("/usermanager/api/v1/users", api_key=api_key, payload={
          "user_name": username,
          "wallet_name": username,
          "admin_id": admin_key,
        })
        wallet = json['wallets'][0]
        return wallet["user"], wallet["id"], wallet["adminkey"]


    def create_user_lnurlw(self, username, api_key, wallet_id) -> str:
        json = self.request("/withdraw/api/v1/links", api_key=api_key, payload={
            "wallet_id": wallet_id,
            "title": f"personal lnurlw for {username}",
            "min_withdrawable": 10,
            "max_withdrawable": 1_000_000,
            "uses": 250,
            "wait_time": 1,
            "is_unique": False,
            "use_custom": False,
        })
        return json["lnurl"]


    def create_user_tpos(self, username, api_key) -> str:
        try:
            json = self.request("/tpos/api/v1/tposs", api_key=api_key, payload={
                "name": f"tpos for {username}",
                "currency": "EUR",
                "tip_options": "[]",
                "tip_wallet": "",
            })
            return json["id"]
        except Exception as e:
            print(e)
            print("failed tpos")
            raise Exception(e)


    def create_payment(self, api_key, bolt11) -> str:
        json = self.request("/api/v1/payments", api_key=api_key, payload={
            "bolt11": bolt11,
        })
        return json.get("payment_hash")


    def create_user_lnurlp(self, username, api_key, wallet_id) -> str:
        webhook = self._config["webhook"]["url"]
        webhook_secret = self._config["webhook"]["secret"]
        json = self.request("/lnurlp/api/v1/links", api_key=api_key, payload={
            "wallet_id": wallet_id,
            "description": f"personal lnurlp for {username}",
            "min": 1,
            "max": 10_000_000,
            "comment_chars": 200,
            "webhook_url": f"{webhook}/payment?api_key={webhook_secret}&username={username}",
            "success_text": f"thank you! {username}",
        })
        return json["lnurl"]

# TODO: add websocket listener and forward
# /api/v1/payments/sse?api-key=c80bda73f47f4539ad2514d9b409c1da

    def create_lnurlp(self, instance_id) -> str:
        price = self._config.lnbits.price()
        webhook = self._config.webhook.url()
        webhook_secret = self._config.webhook.secret()
        json = self.request("/lnurlp/api/v1/links", payload={
            "description": f"top up for instance: {instance_id}",
            "min": price,
            "max": price * 10,
            "comment_chars": 0,
            "webhook_url": f"{webhook}/payment?api_key={webhook_secret}&instance_id={instance_id}",
            "success_text": "instance stop date extended, if it is your first payment, it will take 45-60 seconds until the admin url will be visible!",
        }, api_key=self._config.lnbits.api_key)
        return json["lnurl"]
