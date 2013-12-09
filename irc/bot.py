import asyncio
import irc.client
import irc.messages
import irc.codes
import irc.plugins
import irc.handler


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_prefix = ';'
        self.command_handlers = {}
        self.plugins = {}

        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)
        # TODO configure which builtin plugins to load
        self.load_plugin('admin', '/home/tron/dev/irc-env/irc/irc/plugins/admin.py')

        self.starting_channels = ['#testbotz']
        self.owner = kwargs.get('owner')

    def valid_command(self, message):
        msg = message.params[1]
        return msg.startswith(self.command_prefix)

    def destination(self, command):
        if command.target == self.nick:
            return command.sender
        else:
            return command.target

    def unload_plugin(self, plugin_name):
        plugin = self.plugins[plugin_name]
        cmd_handlers, msg_handlers = irc.plugins.get_handlers(plugin)

        for irc_command, handler in msg_handlers.items():
            handlers = self.msg_handlers[irc_command.upper()]
            handlers.remove(handler)

        for cmd in cmd_handlers.keys():
            del self.command_handlers[cmd]

    def load_plugin(self, name, path):
        plugin_class = irc.plugins.get_plugin(name, path)
        plugin = plugin_class(self)
        # TODO reinit plugins dependent on plugin_class
        if plugin_class.__name__ in self.plugins:
            self.unload_plugin(plugin_class.__name__)
        self.plugins[plugin_class.__name__] = plugin

        cmd_handlers, msg_handlers = irc.plugins.get_handlers(plugin)

        for irc_command, handler in msg_handlers.items():
            self.add_handler(irc_command.upper(), handler)

        self.command_handlers.update(cmd_handlers)

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
    for c in bot.starting_channels:
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