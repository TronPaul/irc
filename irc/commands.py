import irc.protocol as protocol


class Command(protocol.Message):
    def __init__(self, params, command=None, prefix=None):
        if command is None:
            command = self.__class__.__name__.upper()
        super().__init__(command, params, prefix=prefix)


class Nick(Command):
    def __init__(self, nick, prefix=None):
        params = [nick]
        super().__init__(params, prefix=prefix)


class User(Command):
    def __init__(self, username, hostname, servername, realname, prefix=None):
        params = [username, hostname, servername, realname]
        super().__init__(params, prefix=prefix)


class Join(Command):
    def __init__(self, channel, password=None):
        params = [channel]
        if password:
            params.append(password)
        super().__init__(params)


class Ping(Command):
    def __init__(self, params, prefix=None):
        super().__init__(params, prefix=prefix)


class Pong(Command):
    def __init__(self, params, prefix=None):
        super().__init__(params, prefix=prefix)


class Pass(Command):
    def __init__(self, password):
        params = [password]
        super().__init__(params)


class PrivMsg(Command):
    def __init__(self, target, message):
        params = [target, message]
        super().__init__(params)