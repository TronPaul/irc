import logging
import functools
import asyncio
import asyncio.queues
import inspect
import irc.protocol
import irc.parser
import irc.messages
import irc.codes

IRC_LOG = logging.getLogger('irc')
MESSAGE_LOG = logging.getLogger('irc.message')
MESSAGE_LOG_FORMAT = '{dir} Message: {message}'


# TODO add connection timeout RE: Gamesurge
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

    _read_handler = None
    _send_handler = None

    def __init__(self, host, nick, *args, ssl=False, port=6667, username=None,
                 realname=None, hostname=None, password=None, throttle=None,
                 loop=None, message_log=MESSAGE_LOG,
                 message_log_format=MESSAGE_LOG_FORMAT, **kwargs):
        self.host = host
        self.port = port
        self.ssl = ssl

        self.attempted_nick = nick
        self.password = password
        self.realname = realname or nick
        self.username = username or nick
        self.hostname = hostname or host

        self._loop = loop or asyncio.get_event_loop()
        self._send_queue = asyncio.queues.Queue(loop=self.loop)
        self.tasks = asyncio.queues.JoinableQueue(loop=self.loop)
        self.throttle = throttle

        self.message_log = message_log
        self.message_log_format = message_log_format
        self.msg_handlers = {}

    @property
    def loop(self):
        return self._loop

    @asyncio.coroutine
    def start(self):
        conn_task = self._connect()
        self._transport, protocol = yield from conn_task
        IRC_LOG.debug('Connected')
        self._register()
        self._read_handler = asyncio.async(self._read_loop(protocol), loop=self.loop)
        self._send_handler = asyncio.async(self._send_loop(), loop=self.loop)

    def _connect(self):
        conn = _connect(self.host, self.port, self.ssl, self.loop)
        conn_task = asyncio.async(conn, loop=self.loop)
        return conn_task

    def _register(self):
        IRC_LOG.debug('Registering')
        if self.password:
            self.send_message(irc.messages.Pass(self.password))
        self.send_nick(self.attempted_nick)
        self.send_message(irc.messages.User(self.attempted_nick, self.attempted_nick, 'tulip-irc', self.attempted_nick))

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
                    handler_task = yield from handler
                    self.tasks.put_nowait(handler_task)
                    handler_task.add_done_callback(self.cleanup_handler_task)
            except irc.parser.EofStream:
                break
            except irc.protocol.ProtocolViolationError as e:
                IRC_LOG.warn('Recieved malformed message "{raw}"'.format(raw=e.raw))

    def cleanup_handler_task(self, handler_task):
        self.tasks.task_done()

    @asyncio.coroutine
    def _send_loop(self):
        next_send = self.loop.time() if self.throttle else None
        while True:
            raw = yield from self._send_queue.get()
            if next_send and next_send > self.loop.time():
                yield from asyncio.sleep(next_send - self.loop.time(), loop=self.loop)
            self._transport.write(raw)
            if self.throttle:
                next_send = self.loop.time() + self.throttle

    def log_message(self, message, sending=False):
        direction = 'SEND' if sending else 'RECV'
        self.message_log.info(self.message_log_format.format(
            dir=direction, message=message))

    def handles(self, irc_command):
        def decorator(f):
            assert asyncio.tasks.iscoroutinefunction(f)
            self.add_handler(irc_command, f)
            return f

        return decorator

    def add_handler(self, irc_command, f):
        assert asyncio.tasks.iscoroutinefunction(f)
        if irc_command not in self.msg_handlers:
            self.msg_handlers[irc_command] = []
        self.msg_handlers[irc_command].append(f)

    @asyncio.coroutine
    def handle_message(self, message):
        # handle irc protocol commands
        if message.command == 'PING':
            yield from self.send_message(irc.messages.Pong(message.params))
        # TODO: check for race condition
        elif message.command == irc.codes.RPL_WELCOME:
            self.registered = True
            self.nick = self.attempted_nick
            self.attempted_nick = None
        elif message.command in [irc.codes.ERR_NICKNAMEINUSE, irc.codes.ERR_ERRONEUSNICKNAME]:
            yield from self.send_nick(self.attempted_nick + '_')
        elif message.command == 'NICK' and message.nick == self.nick:
            self.nick = message.params[0]
            self.attempted_nick = None
        elif message.command == irc.codes.ERR_PASSWDMISMATCH:
            raise irc.codes.PasswordMismatchError

        handlers = self.msg_handlers.get(message.command, [])
        return asyncio.gather(*[h(self, message) for h in handlers], loop=self.loop)

    def quit(self):
        fut = self.send_message(irc.messages.Quit())

        def cancel(fut):
            self._read_handler.cancel()
            self._send_handler.cancel()

        fut.add_done_callback(cancel)
        return fut

    def send_nick(self, nick):
        self.attempted_nick = nick
        return self.send_message(irc.messages.Nick(nick))

    def send_privmsg(self, target, message):
        return self.send_message(irc.messages.PrivMsg(target, message))

    def send_message(self, message):
        self.log_message(message, sending=True)
        return self.send_raw(message.encode())

    def send_raw(self, raw):
        assert type(raw) == bytes
        return asyncio.async(self._send_queue.put(raw), loop=self.loop)
