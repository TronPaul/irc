import asyncio
import irc
import irc.client
import irc.messages
import irc.codes
import irc.handler


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = kwargs.get('config', {})
        self.command_prefix = self.config.get('COMMAND_PREFIX', ';')
        self.command_handlers = {}

        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)

    def valid_command(self, message):
        msg = message.params[1]
        return msg.startswith(self.command_prefix)

    def destination(self, command):
        if command.target == self.nick:
            return command.sender
        else:
            return command.target

    def add_command_handler(self, command, handler):
        self.command_handlers[command] = handler

    def handles_command(self, command_name):
        def decorator(f):
            f = irc.handler.command_handler(f)
            self.add_command_handler(command_name, f)
            return f

        return decorator


@irc.handler.message_handler
def handle_welcome(bot, _):
    for c in bot.config['STARTING_CHANNELS']:
        bot.send_message(irc.messages.Join(c))


@irc.handler.message_handler
def handle_privmsg(bot, message):
    if bot.valid_command(message):
        sender = message.nick
        target = message.params[0]
        msg = message.params[1]
        if ' ' in msg:
            cmd, msg = msg[1:].split(' ', 1)
            params = msg.split(' ')
        else:
            cmd, msg, params = msg[1:], '', []

        command = irc.handler.Command(sender, cmd, target, params)

        if cmd in bot.command_handlers:
            asyncio.Task(bot.command_handlers[cmd](bot, command), loop=bot.loop)
