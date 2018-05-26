
from zope import component

from ctrl.core.extension import CtrlExtension
from ctrl.core.interfaces import (
    ICommandRunner, ICtrlExtension, ISubcommand, IVPNctl)

from .command import VPNSubcommand
from .vpnctl import VPNctl


class CtrlVPNExtension(CtrlExtension):

    def register_adapters(self):
        component.provideAdapter(
            factory=VPNSubcommand,
            adapts=[ICommandRunner],
            provides=ISubcommand,
            name='vpn')

    async def register_utilities(self):
        component.provideUtility(
            VPNctl(),
            provides=IVPNctl)


# register the extension
component.provideUtility(
    CtrlVPNExtension(),
    ICtrlExtension,
    'vpn')
