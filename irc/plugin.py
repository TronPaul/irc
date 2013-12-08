import inspect
import importlib
import irc.handler


class PluginLoadError(Exception):
    pass


def get_handler_dict(name, path):
    try:
        module = reload_module(name, path)
        Plugin = get_plugin(module)
        handler_types = get_handlers(Plugin)
        return [{h.__name__: h for h in handlers} for handlers in handler_types]
    except:
        raise PluginLoadError


def reload_module(name, path):
    loader = importlib.find_loader(name, path)
    if not loader:
        raise ImportError
    return loader.load_module()


def get_plugin(module):
    if not inspect.ismodule(module):
        raise TypeError
    return module.Plugin


def get_handlers(plugin):
    cmd_handlers = []
    msg_handlers = []
    for attr_name in dir(plugin):
        attr = getattr(plugin, attr_name)
        if irc.handler.is_command_handler(attr):
            cmd_handlers.append(attr)
        elif irc.handler.is_message_handler(attr):
            msg_handlers.append(attr)
    return cmd_handlers, msg_handlers