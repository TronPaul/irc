import asyncio
import logging
from irc import IrcBot

l = logging.getLogger('irc')
l.setLevel(logging.DEBUG)
h = logging.StreamHandler()
h.setLevel(logging.DEBUG)
l.addHandler(h)
bot = IrcBot('irc.geeksirc.net', 'TulipBot')

@bot.handles_command('echo')
@asyncio.coroutine
def echo(bot, command):
    bot.send_privmsg(command.target, command.params_string)


def start():
    asyncio.Task(bot.start())
    asyncio.get_event_loop().run_forever()

start()
