import asyncio
import asyncio.tasks
import inspect


class Command:
    def __init__(self, command, target, params):
        self.command = command
        self.target = target
        self.params = params

    @property
    def params_string(self):
        return ' '.join(self.params)


def is_handler(f):
    return (inspect.isfunction(f) or inspect.ismethod(f)) and asyncio.tasks.iscoroutinefunction(f)


def is_message_handler(f):
    return is_handler(f) and getattr(f, 'message_handler', False)


def is_command_handler(f):
    return is_handler(f) and getattr(f, 'command_handler', False)


def handler(f):
    if not inspect.isfunction(f):
        raise TypeError
    if not asyncio.tasks.iscoroutinefunction(f):
        f = asyncio.coroutine(f)
    return f


def message_handler(f):
    f = handler(f)
    f.message_handler = True
    return f


def command_handler(f):
    f = handler(f)
    f.command_handler = True
    return f