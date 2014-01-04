import collections
import enum


class LastParamType(enum.Enum):
    normal = 1
    string = 2
    list_ = 3


class ParamsParseError(ValueError):
    pass


def empty_parser(params_string):
    if params_string:
        raise ParamsParseError


CommandHandler = collections.namedtuple('CommandHandler', ['params_parser', 'command_function'])


def make_params_parser(name, param_names, last_collects=LastParamType.normal, default_values=None):
    params_class = collections.namedtuple(name, param_names)

    def params_parser(params_string):
        if last_collects == LastParamType.list_ or last_collects == LastParamType.string:
            all_items = params_string.split(maxsplit=len(param_names)-1)
            if len(all_items) >= len(param_names):
                if last_collects == LastParamType.list_:
                    params = all_items[:-1]
                    rest = all_items.pop()
                    params.append(rest.split())
                elif last_collects == LastParamType.string:
                    params = all_items[:-1]
                    rest = all_items.pop()
                    params.append(rest)
                else:
                    raise NotImplementedError
            else:
                params = all_items
        else:
            params = params_string.split()

        if default_values and len(params) < len(param_names):
            params.extend(default_values[len(params) - len(param_names):])

        if len(params) == len(param_names):
            kwargs = dict(zip(param_names, params))
            return params_class(**kwargs)
        else:
            raise ParamsParseError(params_string)
    return params_parser


class Command:
    def __init__(self, sender, command, target, params):
        self.sender = sender
        self.command = command
        self.target = target
        self.params = params

    def reply(self, bot, message):
        dest = bot.destination(self)
        return bot.send_privmsg(dest, message)