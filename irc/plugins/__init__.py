import importlib.machinery
import irc.handler


class PluginLoadError(Exception):
    pass


class BasePlugin:
    dependencies = []

    def __init__(self, bot):
        if not self.check_dependencies(bot):
            raise PluginLoadError

    def check_dependencies(self, bot):
        return all([dep in bot.plugins for dep in self.dependencies])


def load_module(name, path):
    loader = importlib.machinery.SourceFileLoader(name, path)
    if not loader:
        raise ImportError
    return loader.load_module()


def get_plugin(name, path):
    try:
        module = load_module(name, path)
        return module.Plugin
    except Exception as e:
        raise PluginLoadError from e


def get_handlers(plugin):
    cmd_handlers = {}
    msg_handlers = {}
    for attr_name in dir(plugin):
        attr = getattr(plugin, attr_name)
        if irc.handler.is_command_handler(attr):
            cmd_handlers[attr_name] = attr
        elif irc.handler.is_message_handler(attr):
            msg_handlers[attr_name] = attr
    return cmd_handlers, msg_handlers