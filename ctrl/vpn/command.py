
import asyncio
import os

from zope import interface
from zope.dottedname.resolve import resolve
import zope.event

from ctrl.core.constants import RUN_FOREVER
from ctrl.core.interfaces import ISubcommand

from .events import VPNStatusEvent


class VPNMonitorCommand(object):

    def __init__(self, socket):
        self.socket = socket
        self._reading = False

    @property
    def monitor(self):
        if 'VPN_MONITOR' in os.environ:
            router = os.environ['VPN_MONITOR'].split(' ')
            return router[0]

    async def connect(self):
        return await asyncio.open_unix_connection(self.socket)

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

    async def handle(self, *args, loop=None):
        if self.monitor:
            await resolve(self.monitor)().monitor()
        self.reader, self.writer = await self.connect()
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


@interface.implementer(ISubcommand)
class VPNSubcommand(object):

    def __init__(self, context):
        self.context = context

    async def handle(self, command, *args, loop=None):
        return await getattr(self, 'handle_%s' % command)(*args, loop=loop)

    async def handle_monitor(self, server_addr, *args, loop=None):
        return await VPNMonitorCommand(server_addr).handle(*args)
