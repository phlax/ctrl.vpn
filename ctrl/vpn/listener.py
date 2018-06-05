
import asyncio
import os

from zope.dottedname.resolve import resolve
import zope.event

from ctrl.core.constants import RUN_FOREVER

from .events import VPNStatusEvent


class OpenVPNListener(object):

    def __init__(self, emit, filter_journal=None, loop=None):
        self.loop = loop or asyncio.get_event_loop()

    def reader(self):
        while True:
            resp = self.journal.get_next()
            if not resp:
                break
            asyncio.ensure_future(self.emit(resp))
        self.journal.process()

    def listen(self):
        self.loop.add_reader(self.journal, self.reader)


class VPNListener(object):

    def __init__(self):
        self._reading = False

    @property
    def monitor(self):
        if 'VPN_MONITOR' in os.environ:
            router = os.environ['VPN_MONITOR'].split(' ')
            return router[0]

    async def connect(self, socket):
        return await asyncio.open_unix_connection(socket)

    async def handle_incoming(self):
        wait_for = None
        while True:
            _msg = (await self.reader.readline()).decode('utf-8')
            if self._reader:
                if await self._reader(_msg):
                    break
            if _msg.startswith('>CLIENT:ESTABLISHED'):
                wait_for = '>CLIENT:ENV,END'
            if wait_for is not None:
                if _msg.strip() == wait_for:
                    await self.status()
                    break
        asyncio.ensure_future(self.handle_incoming())

    async def handle_message(self, msg):
        if msg.startswith('OpenVPN CLIENT LIST'):
            parts = msg.split('\n')
            for i, part in enumerate(parts):
                if part.strip() == 'ROUTING TABLE':
                    routing_starts = i + 2
                if part.strip() == 'GLOBAL STATS':
                    routing_ends = i
            routing = parts[routing_starts:routing_ends]
            routes = {}
            for route in routing:
                route_parts = route.split(',')
                routes[route_parts[1]] = route_parts[0]
            zope.event.notify(VPNStatusEvent(routes))

    async def listen(self, socket, *args, loop=None):
        if self.monitor:
            await resolve(self.monitor)().monitor()
        self.reader, self.writer = await self.connect(socket)
        await self.reader.readline()
        asyncio.ensure_future(self.handle_incoming())
        asyncio.ensure_future(self.poll_for_disconnects())
        return RUN_FOREVER

    async def poll_for_disconnects(self):
        await self.status()
        await asyncio.sleep(20)
        asyncio.ensure_future(self.poll_for_disconnects())

    async def _read_status(self, _msg):
        self._msg += _msg
        if _msg.strip() == 'END':
            await self.handle_message(self._msg)
            return True

    async def status(self):
        self._msg = ''
        self._reader = self._read_status
        self.writer.write(b'status\n')
        self._reading = None

    def state_on(self):
        self.writer.write(b'state on\n')
