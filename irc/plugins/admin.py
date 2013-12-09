import irc.handler
import irc.plugins
import functools
import irc.messages


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
        if len(command.params) != 1:
            raise Exception
        plugin_name = command.params[0]
        bot.unload_plugin(plugin_name)

    @admin_command
    def part(self, bot, command):
        if len(command.params) != 1:
            raise Exception
        channel = command.params[0]
        bot.send_message(irc.messages.Part(channel))

    @admin_command
    def join(self, bot, command):
        if len(command.params) != 1:
            raise Exception
        channel = command.params[0]
        bot.send_message(irc.messages.Join(channel))

    @admin_command
    def quit(self, bot, command):
        bot.quit()

    @admin_command
    def raw(self, bot, command):
        bot.send_raw(command.params_string)


Plugin = AdminPlugin