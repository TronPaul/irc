import asyncio
import irc.client
import irc.messages
import irc.codes
import irc.plugin
import irc.command


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_prefix = ';'
        self.command_handlers = {}
        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)
        self.add_command_handler('load', handle_load)

        self.starting_channels = ['#testbotz']

    def valid_command(self, message):
        target = message.params[0]
        msg = message.params[1]
        return target != self.nick and msg.startswith(self.command_prefix)

    def load_plugin(self, name, path):
        handlers = irc.plugin.get_handler_dict(name, path)
        self.command_handlers.update(handlers)

    def add_command_handler(self, command, handler):
        self.command_handlers[command] = handler

    def handles_command(self, command_name):
        def decorator(f):
            f = irc.command.command_handler(f)
            self.add_command_handler(command_name, f)
            return f

        return decorator


@asyncio.coroutine
def handle_welcome(bot, _):
    for c in bot.starting_channels:
        bot.send_message(irc.messages.Join(c))


@asyncio.coroutine
def handle_privmsg(bot, message):
    if bot.valid_command(message):
        target = message.params[0]
        msg = message.params[1]
        cmd, msg = msg[1:].split(' ', 1)
        params = msg.split(' ')

        command = irc.command.Command(cmd, target, params)

        if cmd in bot.command_handlers:
            asyncio.Task(bot.command_handlers[cmd](bot, command), loop=bot.loop)

@irc.command.command_handler
def handle_load(bot, command):
    if len(command.params) != 2:
        raise Exception
    name, path = command.params
    bot.load_plugin(name, path)