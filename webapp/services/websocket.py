import asyncio

from enum import Enum, auto
from abc import ABC, abstractmethod

from fastapi import WebSocket, WebSocketDisconnect

from webapp.models import User
from webapp.services.lnbits import LnbitsService
from webapp.services.login import LoginService


class WsType(Enum):
    ping = auto()
    pay = auto()
    user = auto()
    invoice = auto()
    create_invoice = auto()
    pay_lnurlp = auto()
    pay_lnurlw = auto()
    unhandled = auto()


class WsAction(ABC):
    def __init__(self, action_type: WsType, lnbits_service: LnbitsService):
        self.type = action_type
        self._lnbits_service = lnbits_service

    @abstractmethod
    def execute(self, user: User, data: dict) -> dict:
        """ called when websocket action is dispatched """

    def return_with_type(self, data) -> dict:
        return  {
            "type": self.type.name,
            "data": data,
        }

class WsUnhandledAction(WsAction):
    def execute(self, *_) -> dict:
        return self.return_with_type({"message": "unhandled"})

class WsPingAction(WsAction):
    def execute(self, *_) -> dict:
        return self.return_with_type({"message": "pong"})

class WsUserAction(WsAction):
    def execute(self, user: User, _) -> dict:
        payments = self._lnbits_service.get_payments(user.api_key)
        balance = self._lnbits_service.get_balance(user.api_key)
        return self.return_with_type({
            "username": user.username,
            "usr": user.usr,
            "wallet_id": user.wallet_id,
            "api_key": user.api_key,
            "lnurlp": user.lnurlp,
            "lnurlw": user.lnurlw,
            "tpos": user.tpos,
            "payments": payments,
            "balance": balance,
        })

class WsCreateInvoiceAction(WsAction):
    def execute(self, user: User, data) -> dict:
        amount = data.get("amount")
        if not amount or amount <= 0:
            return {"type": "error", "message": "invalid amount"}
        payment_hash, payment_request = self._lnbits_service.create_invoice(user.api_key, amount, str(data.get("description")))
        return self.return_with_type({
            "invoice": payment_request,
            "payment_hash": payment_hash,
        })

class WsPayAction(WsAction):
    def execute(self, user: User, data) -> dict:
        try:
            payment_hash = self._lnbits_service.create_payment(user.api_key, data.get("bolt11"))
            return self.return_with_type({"payment_hash": payment_hash})
        except Exception as exc:
            print("Error: paying invoice")
            print(exc)
            return {"type": "error", "message": str(exc) }

class WsInvoiceAction(WsAction):
    def execute(self, _: User, data) -> dict:
        try:
            bolt11 = data.get("bolt11")
            if not bolt11:
                raise Exception("no bolt11")
            invoice = self._lnbits_service.decode_invoice(bolt11)
            if "payment_hash" in invoice:
                return self.return_with_type(invoice)
            elif "domain" in invoice:
                lnurl = self._lnbits_service.decode_lnurl(invoice.get("domain"))
                return {"type": "lnurl", "data": lnurl}
            else:
                return {"type": "error", "message": "unhandled"}
        except Exception as exc:
            print(exc)
            return {"type": "error", "message": str(exc) }


class WsLnurlpAction(WsAction):
    def execute(self, user: User, data) -> dict:
        try:
            callback = data.get("callback")
            amount = data.get("amount")
            if not callback or not amount:
                return {"type": "error", "message": "invalid amount or callback"}
            comment = data.get("comment")
            bolt11, successMessage = self._lnbits_service.get_lnurl_invoice(callback, amount, comment)
            payment_hash = self._lnbits_service.create_payment(user.api_key, bolt11)
            return {"type": "lnurl_success", "data": { "payment_hash": payment_hash, "message": successMessage }}
        except Exception as exc:
            print(exc)
            return {"type": "error", "message": str(exc) }

class WsLnurlwAction(WsAction):
    def execute(self, user: User, data) -> dict:
        try:
            callback = data.get("callback")
            amount = data.get("amount")
            k1 = data.get("k1")
            if not callback or not amount or not k1:
                return {"type": "error", "message": "invalid amount or callback or k1"}
            payment_hash, payment_request = self._lnbits_service.create_invoice(user.api_key, amount)
            self._lnbits_service.send_withdraw(callback, k1, payment_request)
            return {"type": "lnurl_success", "data": { "payment_hash": payment_hash, "message": "withdrawn" }}
        except Exception as exc:
            print(exc)
            return {"type": "error", "message": str(exc) }


class WebSocketDispatcher():
    def __init__(self, lnbits_service: LnbitsService):
        self._lnbits_service = lnbits_service
        self.actions: list[WsAction] = []

        self.unhandled: WsAction = self.create_action(WsType.unhandled, WsUnhandledAction)

        self.add_action(WsType.ping, WsPingAction)
        self.add_action(WsType.invoice, WsInvoiceAction)
        self.add_action(WsType.create_invoice, WsCreateInvoiceAction)
        self.add_action(WsType.user, WsUserAction)
        self.add_action(WsType.pay, WsPayAction)
        self.add_action(WsType.pay_lnurlp, WsLnurlpAction)
        self.add_action(WsType.pay_lnurlw, WsLnurlwAction)

    def create_action(self, action_type: WsType, action) -> WsAction:
        return action(action_type, self._lnbits_service)

    def add_action(self, action_type: WsType, action) -> None:
        self.actions.append(self.create_action(action_type, action))

    def get_action(self, action_type: WsType) -> WsAction:
        search_action = [action for action in self.actions if action.type.name == action_type]
        found_action = self.unhandled
        if len(search_action) > 0:
            found_action = search_action.pop()
        return found_action

    def dispatch(self, user, action_type: WsType, data) -> dict:
        action = self.get_action(action_type)
        return action.execute(user, data)


class WebSocketService():
    def __init__(self, login_service: LoginService, lnbits_service: LnbitsService):
        self._login_service = login_service
        self._lnbits_service = lnbits_service
        self.queue: asyncio.Queue = asyncio.Queue()
        self.tasks: list = []
        self.dispatcher = WebSocketDispatcher(lnbits_service)
        self.user: None | User = None

    async def handle_websocket_message(self, websocket: WebSocket, data):
        print("handle_websocket_message")
        print(data.get("type"))
        if self.user:
            action_data = self.dispatcher.dispatch(self.user, data.get("type"), data.get("data"))
            await websocket.send_json(action_data)

    async def start_listener(self, websocket: WebSocket, token: str):
        self.user = await self._login_service.user(token)
        task_read = asyncio.create_task(self.read_from_socket(websocket))
        task_send = asyncio.create_task(self.get_data_and_send(websocket))
        self.tasks.append(task_read)
        self.tasks.append(task_send)
        task = asyncio.gather(task_read, task_send)
        try:
            await task
        except:
            raise
        finally:
            task.cancel()

        return task


    async def cancel_listener(self):
        print("cancels websocket")
        for task in self.tasks:
            task.cancel()

    async def read_from_socket(self, websocket: WebSocket):
        async for data in websocket.iter_json():
            self.queue.put_nowait(data)

    async def get_data_and_send(self, websocket: WebSocket):
        while True:
            if self.queue.empty():
                await asyncio.sleep(1)
            else:
                data = self.queue.get_nowait()
                await self.handle_websocket_message(websocket, data)
