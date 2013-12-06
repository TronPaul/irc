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


def is_command_handler(f):
    return (inspect.isfunction(f) or inspect.ismethod(f)) and getattr(f, 'command_handler',
                                                                      False) and asyncio.tasks.iscoroutinefunction(f)


def command_handler(f):
    if not inspect.isfunction(f):
        raise TypeError
    if not asyncio.tasks.iscoroutinefunction(f):
        f = asyncio.coroutine(f)
    f.command_handler = True
    return f