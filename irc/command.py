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


def make_params_parser(name, param_names, last_collects=LastParamType.normal):
    params_class = collections.namedtuple(name, param_names)

    def params_parser(params_string):
        if last_collects == LastParamType.list_:
            all_items = params_string.split(maxsplit=len(param_names)-1)
            params = all_items[:-1]
            rest = all_items.pop()
            params.append(rest.split())
        elif last_collects == LastParamType.string:
            all_items = params_string.split(maxsplit=len(param_names)-1)
            params = all_items[:-1]
            rest = all_items.pop()
            params.append(rest)
        else:
            params = params_string.split()

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
        bot.send_privmsg(dest, message)