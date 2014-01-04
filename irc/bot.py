import asyncio
import irc.client
import irc.command
import irc.messages
import irc.codes

BASE_HELP_MSG = """
                Commands: {commands}
                For help with commands use `{prefix}help COMMAND`
                """


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = kwargs.get('config', {})
        self.command_prefix = self.config.get('COMMAND_PREFIX', ';')
        self.command_handlers = {}

        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)
        self.add_command_handler('help', handle_help, ['command'], default_values=[None])

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

    def add_command_handler(self, command, f, params=None, last_collects=irc.command.LastParamType.normal, default_values=None):
        if params:
            parse_fn = irc.command.make_params_parser(command, params, last_collects=last_collects, default_values=default_values)
        else:
            parse_fn = irc.command.empty_parser

        self.command_handlers[command] = irc.command.CommandHandler(parse_fn, f)

    def handles_command(self, command_name, params=None, last_collects=False, default_values=None):

        def decorator(f):
            assert asyncio.tasks.iscoroutinefunction(f)
            self.add_command_handler(command_name, f, params, last_collects=last_collects, default_values=default_values)
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

            yield from handler.command_function(bot, command)


@asyncio.coroutine
def handle_help(bot, command):
    """Get help text for commands"""
    command_str = command.params.command
    if not command_str:
        commands = ', '.join(bot.command_handlers.keys())
        msg = BASE_HELP_MSG.format(commands=commands, prefix=bot.command_prefix)
    else:
        handler = bot.command_handlers.get(command_str, None)
        if not handler:
            help_text = 'Does not exist'
        else:
            help_text = handler.command_function.__doc__
        msg = '{0}: {1}'.format(command_str, help_text.strip())
    for line in msg.split('\n'):
        yield from command.reply(bot, line.strip())