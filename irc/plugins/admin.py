import irc.handler
import irc.plugins
import functools


def admin_command(f):
    f = irc.handler.command_handler(f)
    @functools.wraps(f)
    def wrapper(self, bot, command, *args, **kwargs):
        if not is_admin(bot, command.sender):
            command.reply(bot, '{0} does not have permission for {1}'.format(command.sender, 'load'))
            raise PermissionError
        return f(self, bot, command, *args, **kwargs)
    return wrapper


def is_admin(bot, nick):
    return bot.owner is not None and bot.owner == nick


class AdminPlugin(irc.plugins.BasePlugin):
    @admin_command
    def load(self, bot, command):
        if len(command.params) != 2:
            raise Exception
        name, path = command.params
        bot.load_plugin(name, path)

    @admin_command
    def unload(self, bot, command):
        pass

    @admin_command
    def part(self, bot, command):
        pass

    @admin_command
    def join(self, bot, command):
        pass

    @admin_command
    def quit(self, bot, command):
        pass

    @admin_command
    def raw(self, bot, command):
        pass


Plugin = AdminPlugin