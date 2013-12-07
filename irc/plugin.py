import inspect
import importlib
import irc.command


class PluginLoadError(Exception):
    pass


def get_handler_dict(name, path):
    try:
        module = reload_module(name, path)
        Plugin = get_plugin(module)
        handlers = get_handlers(Plugin)
        return {h.__name__: h for h in handlers}
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
    handlers = []
    for attr_name in dir(plugin):
        attr = getattr(plugin, attr_name)
        if irc.command.is_command_handler(attr):
            handlers.append(attr)
    return handlers