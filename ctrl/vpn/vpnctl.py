from zope import interface


from ctrl.core.interfaces import IVPNctl


@interface.implementer(IVPNctl)
class VPNctl(object):

    pass
