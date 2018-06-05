
from zope import component, interface

from ctrl.core.interfaces import ISubcommand, IVPNListener


@interface.implementer(ISubcommand)
class VPNSubcommand(object):

    def __init__(self, context):
        self.context = context

    async def handle(self, command, *args, loop=None):
        return await getattr(
            self, 'handle_%s' % command)(*args, loop=loop)

    async def handle_monitor(self, server_addr, *args, loop=None):
        return await component.getUtility(
            IVPNListener).connect(server_addr, *args)
