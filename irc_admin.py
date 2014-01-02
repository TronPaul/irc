import functools
import asyncio
import irc.messages
import irc.command


def admin_command_handler(admin_check, f):
    @functools.wraps(f)
    def wrapper(bot, command, *args, **kwargs):
        if not admin_check(command.sender):
            command.reply(bot, '{0} does not have permission for {1}'.format(command.sender, command.command))
            raise PermissionError
        return f(bot, command, *args, **kwargs)
    return wrapper


class Admin:
    def __init__(self, bot=None):
        if bot:
            self.init_bot(bot)
        else:
            self.bot = None

    def init_bot(self, bot):
        bot.config.setdefault('OWNER', None)
        self.bot = bot
        self.handles_admin_command('join', ['channel'])(join)
        self.handles_admin_command('part', ['channel'])(part)
        self.handles_admin_command('quit')(quit)
        self.handles_admin_command('raw', ['raw_string'], irc.command.LastParamType.string)(raw)

    @property
    def owner(self):
        return self.bot.config['OWNER']

    def add_admin_command_handler(self, command, f):
        self.bot.add_command_handler(command, f)

    def is_admin(self, nick):
        return self.owner is not None and nick == self.owner

    def handles_admin_command(self, command, params=None, last_collects=False):
        def decorator(f):
            f = admin_command_handler(self.is_admin, f)
            self.bot.add_command_handler(command, f, params, last_collects=last_collects)
            return f
        return decorator


@asyncio.coroutine
def join(bot, command):
    if len(command.params) != 1:
        raise Exception
    channel = command.params.channel
    return bot.send_message(irc.messages.Join(channel))


@asyncio.coroutine
def part(bot, command):
    if len(command.params) != 1:
        raise Exception
    channel = command.params.channel
    return bot.send_message(irc.messages.Part(channel))


@asyncio.coroutine
def quit(bot, command):
    return bot.quit()


@asyncio.coroutine
def raw(bot, command):
    return bot.send_raw(bytes(command.params.raw_string + '\r\n', encoding='utf8'))