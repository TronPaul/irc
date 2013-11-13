import irc.protocol as protocol

class Command(protocol.Message):
    def __init__(self, params, command=None, prefix=None):
        if command is None:
            command = self.__class__.__name__.upper()
        super(Command, self).__init__(command, params, prefix=prefix)

class Nick(Command):
    def __init__(self, nick, prefix=None):
        params = [nick]
        super(Nick, self).__init__(params, prefix=prefix)

class User(Command):
    def __init__(self, username, hostname, servername, realname, prefix=None):
        params = [username, hostname, servername, realname]
        super(User, self).__init__(params, prefix=prefix)

class Ping(Command):
    def __init__(self, params, prefix=None):
        super(Ping, self).__init__(params, prefix=prefix)

class Pong(Command):
    def __init__(self, params, prefix=None):
        super(Pong, self).__init__(params, prefix=prefix)

class Pass(Command):
    def __init__(self, password):
        params = [password]
        super(Pass, self).__init__(params)
