import asyncio
import pathlib
import irc
import irc.client
import irc.messages
import irc.codes
import irc.plugins
import irc.handler


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = kwargs.get('config', {})
        self.command_prefix = self.config.get('command_prefix', ';')
        self.command_handlers = {}
        self.plugins = {}
        self.plugin_infos = {}

        self.add_handler('PRIVMSG', handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, handle_welcome)
        # TODO configure which builtin plugins to load
        path = str(pathlib.Path(irc.__path__[0]).joinpath('plugins/admin.py'))
        self.load_plugin('admin', path)

        self.starting_channels = self.config.get('starting_channels', [])
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
        # TODO decide if need to unload module
        [self.unload_plugin(pn) for pn, p in self.plugins.items() if plugin_name in p.dependencies]
        plugin = self.plugins.pop(plugin_name)
        cmd_handlers, msg_handlers = irc.plugins.get_handlers(plugin)

        for irc_command, handler in msg_handlers.items():
            handlers = self.msg_handlers[irc_command.upper()]
            handlers.remove(handler)

        for cmd in cmd_handlers.keys():
            del self.command_handlers[cmd]

    def load_plugin(self, name, path):
        plugin_class = irc.plugins.get_plugin(name, path)
        p_class_name = plugin_class.__name__
        self.plugin_infos[p_class_name] = (name, path)
        plugin = plugin_class(self)
        plugins_to_reload = []
        if p_class_name in self.plugins:
            plugins_to_reload = [pn for pn, p in self.plugins.items() if p_class_name in p.dependencies]
            [self.unload_plugin(pn) for pn in plugins_to_reload]
            self.unload_plugin(p_class_name)
        self.plugins[p_class_name] = plugin

        cmd_handlers, msg_handlers = irc.plugins.get_handlers(plugin)

        for irc_command, handler in msg_handlers.items():
            self.add_handler(irc_command.upper(), handler)

        self.command_handlers.update(cmd_handlers)
        [self.load_plugin(*self.plugin_infos[pn]) for pn in plugins_to_reload]

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
