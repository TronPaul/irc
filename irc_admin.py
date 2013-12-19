import functools
import irc.handler
import irc.messages


def admin_command_handler(admin_check, f):
    f = irc.handler.command_handler(f)
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
        self.handles_admin_command('join')(join)
        self.handles_admin_command('part')(part)
        self.handles_admin_command('quit')(quit)
        self.handles_admin_command('raw')(raw)

    @property
    def owner(self):
        return self.bot.config['OWNER']

    def add_admin_command_handler(self, command, f):
        self.bot.add_command_handler(command, f)

    def is_admin(self, nick):
        return self.owner is not None and nick == self.owner

    def handles_admin_command(self, command):
        def decorator(f):
            f = admin_command_handler(self.is_admin, f)
            self.bot.add_command_handler(command, f)
            return f
        return decorator


def join(bot, command):
    if len(command.params) != 1:
        raise Exception
    channel = command.params[0]
    bot.send_message(irc.messages.Join(channel))


def part(bot, command):
    if len(command.params) != 1:
        raise Exception
    channel = command.params[0]
    bot.send_message(irc.messages.Part(channel))


def quit(bot, command):
    bot.quit()


def raw(bot, command):
    bot.send_raw(bytes(command.params_string + '\r\n', encoding='utf8'))