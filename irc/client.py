import logging
import functools
import asyncio
import inspect
import irc.protocol
import irc.parser
import irc.commands
import irc.codes

IRC_LOG = logging.getLogger('irc')
MESSAGE_LOG = logging.getLogger('irc.message')
MESSAGE_LOG_FORMAT = '{dir} Message: {message}'


@asyncio.coroutine
def _connect(host, port, ssl, loop):
    IRC_LOG.debug('Connecting...')
    transport, proto = yield from loop.create_connection(
        functools.partial(irc.parser.StreamProtocol, loop=loop),
        host, port, ssl=ssl)
    return transport, proto


class IrcClient:
    _transport = None
    _message_parser = irc.protocol.MessageParser()
    registered = False
    nick = None

    _message_handler = None

    def __init__(self, host, nick, ssl=False, port=6667, username=None,
                 realname=None, hostname=None, password=None, loop=None,
                 message_log=MESSAGE_LOG,
                 message_log_format=MESSAGE_LOG_FORMAT):
        self.host = host
        self.port = port
        self.ssl = ssl

        self.attempted_nick = nick
        self.password = password
        self.realname = realname or nick
        self.username = username or nick
        self.hostname = hostname or host

        self._loop = loop or asyncio.get_event_loop()

        self.message_log = message_log
        self.message_log_format = message_log_format
        self.handlers = {}

    @asyncio.coroutine
    def start(self):
        conn_task = self._connect()
        self._transport, protocol = yield from conn_task
        IRC_LOG.debug('Connected')
        self._register()
        self._message_handler = asyncio.async(self._read_loop(protocol), loop=self._loop)

    def _connect(self):
        conn = _connect(self.host, self.port, self.ssl, self._loop)
        conn_task = asyncio.async(conn, loop=self._loop)
        return conn_task

    def _register(self):
        IRC_LOG.debug('Registering')
        if self.password:
            self.send_message(irc.commands.Pass(self.password))
        self.send_nick(self.attempted_nick)
        self.send_message(irc.commands.User(self.attempted_nick, self.attempted_nick, 'tulip-irc', self.attempted_nick))

    @asyncio.coroutine
    def _read_loop(self, protocol):
        messagestream = protocol.set_parser(self._message_parser)
        # read commands
        while True:
            try:
                message = yield from messagestream.read()
                self.log_message(message)
                handler = self.handle_message(message)
                if (inspect.isgenerator(handler) or
                        isinstance(handler, asyncio.Future)):
                    yield from handler
            except irc.parser.EofStream:
                break
            except irc.protocol.ProtocolViolationError as e:
                IRC_LOG.warn('Recieved malformed message "{raw}"'.format(raw=e.raw))

    def log_message(self, message, sending=False):
        direction = 'SEND' if sending else 'RECV'
        self.message_log.info(self.message_log_format.format(
            dir=direction, message=message))

    def handles(self, command):
        def decorator(f):
            self.add_handler(command, f)
            return f

        return decorator

    def add_handler(self, command, f):
        if command not in self.handlers:
            self.handlers[command] = []
        self.handlers[command].append(f)

    @asyncio.coroutine
    def handle_message(self, message):
        # handle irc protocol commands
        if message.command == 'PING':
            self.send_message(irc.commands.Pong(message.params))
        # TODO: check for race condition
        elif message.command == irc.codes.RPL_WELCOME:
            self.registered = True
            self.nick = self.attempted_nick
            self.attempted_nick = None
        elif message.command in [irc.codes.ERR_NICKNAMEINUSE, irc.codes.ERR_ERRONEUSNICKNAME]:
            self.send_nick(self.attempted_nick + '_')
        elif message.command == 'NICK' and message.nick == self.nick:
            self.nick = message.params[0]
            self.attempted_nick = None
        elif message.command == irc.codes.ERR_PASSWDMISMATCH:
            raise irc.codes.PasswordMismatchError

        handlers = self.handlers[message.command]
        [asyncio.Task(h(self, message), loop=self._loop) for h in handlers]

    def send_message(self, message):
        self.log_message(message, sending=True)
        self._transport.write(message.encode())

    def send_nick(self, nick):
        self.attempted_nick = nick
        self.send_message(irc.commands.Nick(nick))
