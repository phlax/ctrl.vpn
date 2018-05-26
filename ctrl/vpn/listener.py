
import asyncio


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
