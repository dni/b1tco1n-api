import json
import asyncio

import json
import asyncio
import json
import urllib.parse
from abc import ABC, abstractmethod
from enum import Enum, auto

class SSEType(Enum):
    payment_received = auto()
    ping = auto()
    unhandled = auto()

class SSEAction(ABC):
    def __init__(self, action_type: SSEType):
        self.type = action_type

    @abstractmethod
    def execute(self, data):
        """ executes an action """

    def return_with_type(self, data) -> dict:
        return  {
            "type": self.type.name,
            "data": data,
        }


class SSEUnhandled(SSEAction):
    def execute(self, data):
        print(f"unhandled SSE action: {data}")
        return self.return_with_type({"message": "unhandled sse action", "data": data})

class SSEPingAction(SSEAction):
    def execute(self, data):
        print(f"SSE ping event: {data}")
        # return self.return_with_type({"message": "pong", "date": data})
        return None

class SSEPaymentAction(SSEAction):
    def execute(self, data):
        return {"type": self.type.name, "data": data}


class SSEDispatcher():
    def __init__(self):
        self.actions = []
        self.unhandled = SSEUnhandled(SSEType.unhandled)
        self.add_action(SSEPingAction, SSEType.ping)
        self.add_action(SSEPaymentAction, SSEType.payment_received)

    def create_action(self, action, action_type: SSEType) -> SSEAction:
        return action(action_type)

    def add_action(self, action, action_type: SSEType):
        self.actions.append(self.create_action(action, action_type))

    def get_action(self, action_type: str) -> SSEAction:
        search_action = [action for action in self.actions if action.type.name == action_type]
        found_action = self.unhandled
        if len(search_action) > 0:
            found_action = search_action.pop()
        return found_action

    def dispatch(self, action_type: str, data):
        action = self.get_action(action_type)
        return action.execute(data)


class SSEService:
    def __init__(self):
        self.dispatcher = SSEDispatcher()

    async def handler(self, websocket, sse_event):
        event = sse_event.get("event").replace("-", "_")
        action_data = self.dispatcher.dispatch(event, sse_event.get("data"))
        if action_data:
            await websocket.send_json(action_data)

    async def process_sse(self):
        event = await self.reader.readline()
        event = event.decode().strip()
        if event.startswith('event'):
            data = await self.reader.readline()
            data = data.decode().strip()
            if data.startswith('data'):
                event = event.lstrip('event: ')
                data = data.lstrip('data: ')
                try:
                    data = json.loads(data)
                except:
                    """ just a string no json """
                return {
                    'event': event,
                    'data': data,
                }


    async def init_sse_stream(self, url):
        url = urllib.parse.urlsplit(url)
        full_path = '{}?{}'.format(url.path, url.query)
        try:
            self.reader, self.writer = await asyncio.open_connection(url.netloc, 443, ssl=True)
            query = ('GET {path} HTTP/1.0\r\n'
                     'Host: {hostname}\r\n'
                     '\r\n').format(path=full_path, hostname=url.hostname)
            self.writer.write(query.encode('latin-1'))
        except Exception as e:
            print("ERROR: starting sse listener")
            print(url)
            print(e)
            self.cancel_listener()


    async def watch_sse_stream(self, websocket):
        while True:
            sse_event = await self.process_sse()
            if not sse_event:
                await asyncio.sleep(1)
                continue
            await self.handler(websocket, sse_event)

    async def start_listener(self, websocket, url: str):
        await self.init_sse_stream(url)
        self.task = asyncio.create_task(self.watch_sse_stream(websocket))
        await self.task

    def cancel_listener(self):
        self.writer.close()
        self.task.cancel()
