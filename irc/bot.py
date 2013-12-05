import asyncio
import irc.client
import irc.commands
import irc.codes


class Command:
    def __init__(self, command, target, params):
        self.command = command
        self.target = target
        self.params = params


class IrcBot(irc.client.IrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_prefix = ';'
        self.command_handlers = {}
        self.add_handler('PRIVMSG', self.handle_privmsg)
        self.add_handler(irc.codes.RPL_WELCOME, self.handle_welcome)

        self.starting_channels = ['#testbotz']

    def valid_command(self, message):
        target = message.params[0]
        msg = message.params[1]
        return target != self.nick and msg.startswith(self.command_prefix)

    @staticmethod
    @asyncio.coroutine
    def handle_privmsg(self, message):
        if self.valid_command(message):
            target = message.params[0]
            msg = message.params[1]
            cmd, msg = msg[1:].split(' ', 1)
            params = msg.split(' ')

            command = Command(cmd, target, ' '.join(params))

            handlers = self.command_handlers.get(cmd, [])
            [asyncio.Task(h(self, command), loop=self._loop) for h in handlers]

    @staticmethod
    @asyncio.coroutine
    def handle_welcome(self, message):
        for c in self.starting_channels:
            self.send_message(irc.commands.Join(c))

    def add_command_handler(self, command, f):
        if command not in self.irc_handlers:
            self.command_handlers[command] = []
        self.command_handlers[command].append(f)

    def handles_command(self, command):
        def decorator(f):
            self.add_command_handler(command, f)
            return f

        return decorator