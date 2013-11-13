import asyncio
import logging
from irc import IrcClient

def run():
    l = logging.getLogger('irc')
    l.setLevel(logging.DEBUG)
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)
    l.addHandler(h)
    loop = asyncio.get_event_loop()
    c = IrcClient('irc.freenode.net', 'TulipBot', loop=loop)
    asyncio.Task(c.start())
    loop.run_forever()

run()
