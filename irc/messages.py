import irc.protocol


class Message(irc.protocol.RawMessage):
    def __init__(self, params, command=None, prefix=None):
        if command is None:
            command = self.__class__.__name__.upper()
        super().__init__(command, params, prefix=prefix)


class Nick(Message):
    def __init__(self, nick, prefix=None):
        params = [nick]
        super().__init__(params, prefix=prefix)


class User(Message):
    def __init__(self, username, hostname, servername, realname, prefix=None):
        params = [username, hostname, servername, realname]
        super().__init__(params, prefix=prefix)


class Part(Message):
    def __init__(self, channel, password=None):
        params = [channel]
        if password:
            params.append(password)
        super().__init__(params)


class Join(Message):
    def __init__(self, channel, password=None):
        params = [channel]
        if password:
            params.append(password)
        super().__init__(params)


class Ping(Message):
    def __init__(self, params, prefix=None):
        super().__init__(params, prefix=prefix)


class Pong(Message):
    def __init__(self, params, prefix=None):
        super().__init__(params, prefix=prefix)


class Quit(Message):
    def __init__(self, prefix=None):
        super().__init__([], prefix=prefix)


class Pass(Message):
    def __init__(self, password):
        params = [password]
        super().__init__(params)


class PrivMsg(Message):
    def __init__(self, target, message, prefix=None):
        params = [target, message]
        super().__init__(params, prefix=prefix)