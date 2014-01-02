import asyncio
import irc.client
import irc.command
import irc.messages
import irc.codes


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = kwargs.get('config', {})
        self.command_prefix = self.config.get('COMMAND_PREFIX', ';')
        self.command_handlers = {}

        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)

    def run(self):
        self.loop.run_forever()

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

    def handles_command(self, command_name, params=None, last_collects=False):
        if params:
            parse_fn = irc.command.make_params_parser(command_name, params, last_collects)
        else:
            parse_fn = irc.command.empty_parser

        def decorator(f):
            assert asyncio.tasks.iscoroutinefunction(f)
            self.add_command_handler(command_name, (parse_fn, f))
            return f

        return decorator


@asyncio.coroutine
def handle_welcome(bot, _):
    for c in bot.config['STARTING_CHANNELS']:
        bot.send_message(irc.messages.Join(c))


@asyncio.coroutine
def handle_privmsg(bot, message):
    if bot.valid_command(message):
        sender = message.nick
        target = message.params[0]
        msg = message.params[1]
        if ' ' in msg:
            cmd, params_string = msg[1:].split(' ', 1)
        else:
            cmd, params_string = msg[1:], ''

        if cmd in bot.command_handlers:
            handler = bot.command_handlers[cmd]
            params = handler.params_parser(params_string)
            command = irc.command.Command(sender, cmd, target, params)

            asyncio.Task(handler.command_function(bot, command), loop=bot.loop)