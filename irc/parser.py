import asyncio
import collections
import inspect


class EofStream(Exception):
    """eof stream indication."""


class StreamParser:
    """StreamParser manages incoming bytes stream and protocol parsers.

    StreamParser uses ParserBuffer as internal buffer.

    set_parser() sets current parser, it creates DataQueue object
    and sends ParserBuffer and DataQueue into parser generator.

    unset_parser() sends EofStream into parser and then removes it.
    """

    def __init__(self, *, loop=None, inbuf=None):
        self._loop = loop
        self._eof = False
        self._exception = None
        self._parser = None
        self._output = None
        self._input = inbuf if inbuf is not None else ParserBuffer()

    def is_connected(self):
        return not self._eof

    def exception(self):
        return self._exception

    def set_exception(self, exc):
        self._exception = exc

        if self._output is not None:
            self._output.set_exception(exc)
            self._output = None
            self._parser = None

    def feed_data(self, data):
        """send data to current parser or store in buffer."""
        if not data:
            return

        if self._parser:
            try:
                self._parser.send(data)
            except StopIteration:
                self._output.feed_eof()
                self._output = None
                self._parser = None
            except Exception as exc:
                self._output.set_exception(exc)
                self._output = None
                self._parser = None
        else:
            self._input.feed_data(data)

    def feed_eof(self):
        """send eof to all parsers, recursively."""
        if self._parser:
            try:
                self._parser.throw(EofStream())
            except StopIteration:
                pass
            except EofStream:
                self._output.feed_eof()
            except Exception as exc:
                self._output.set_exception(exc)

            self._parser = None
            self._output = None

        self._eof = True

    def set_parser(self, parser):
        """set parser to stream. return parser's DataQueue."""
        if self._parser:
            self.unset_parser()

        output = DataQueue(loop=self._loop)
        if self._exception:
            output.set_exception(self._exception)
            return output

        # init parser
        p = parser(output, self._input)
        assert inspect.isgenerator(p), 'Generator is required'

        try:
            # initialize parser with data and parser buffers
            next(p)
        except StopIteration:
            pass
        except Exception as exc:
            output.set_exception(exc)
        else:
            # parser still require more data
            self._parser = p
            self._output = output

            if self._eof:
                self.unset_parser()

        return output

    def unset_parser(self):
        """unset parser, send eof to the parser and then remove it."""
        if self._parser is None:
            return

        try:
            self._parser.throw(EofStream())
        except StopIteration:
            pass
        except EofStream:
            self._output.feed_eof()
        except Exception as exc:
            self._output.set_exception(exc)
        finally:
            self._output = None
            self._parser = None


class StreamProtocol(StreamParser, asyncio.Protocol):
    """asyncio's stream protocol based on StreamParser"""

    transport = None

    data_received = StreamParser.feed_data

    eof_received = StreamParser.feed_eof

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        self.transport = None

        if exc is not None:
            self.set_exception(exc)
        else:
            self.feed_eof()


class DataQueue:
    """DataQueue is a destination for parsed data."""

    def __init__(self, *, loop=None):
        self._loop = loop
        self._buffer = collections.deque()
        self._eof = False
        self._waiter = None
        self._exception = None

    def exception(self):
        return self._exception

    def set_exception(self, exc):
        self._exception = exc

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.done():
                waiter.set_exception(exc)

    def feed_data(self, data):
        self._buffer.append(data)

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_result(True)

    def feed_eof(self):
        self._eof = True

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_result(False)

    @asyncio.coroutine
    def read(self):
        if self._exception is not None:
            raise self._exception

        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = asyncio.Future(loop=self._loop)
            yield from self._waiter

        if self._buffer:
            return self._buffer.popleft()
        else:
            raise EofStream


class ParserBuffer(bytearray):
    """ParserBuffer is a bytearray extension.

    ParserBuffer provides helper methods for parsers.
    """

    def __init__(self, *args):
        super().__init__(*args)

        self.offset = 0
        self.size = 0
        self._writer = self._feed_data()
        next(self._writer)

    def _shrink(self):
        if self.offset:
            del self[:self.offset]
            self.offset = 0
            self.size = len(self)

    def _feed_data(self):
        while True:
            chunk = yield
            if chunk:
                chunk_len = len(chunk)
                self.size += chunk_len
                self.extend(chunk)

                # shrink buffer
                if self.offset and len(self) > 8196:
                    self._shrink()

    def feed_data(self, data):
        self._writer.send(data)

    def read(self, size):
        """read() reads specified amount of bytes."""

        while True:
            if self.size >= size:
                start, end = self.offset, self.offset + size
                self.offset = end
                self.size = self.size - size
                return self[start:end]

            self._writer.send((yield))

    def readsome(self, size=None):
        """reads size of less amount of bytes."""

        while True:
            if self.size > 0:
                if size is None or self.size < size:
                    size = self.size

                start, end = self.offset, self.offset + size
                self.offset = end
                self.size = self.size - size

                return self[start:end]

            self._writer.send((yield))

    def readuntil(self, stop, limit=None, exc=ValueError):
        assert isinstance(stop, bytes) and stop, \
            'bytes is required: {!r}'.format(stop)

        stop_len = len(stop)

        while True:
            pos = self.find(stop, self.offset)
            if pos >= 0:
                end = pos + stop_len
                size = end - self.offset
                if limit is not None and size > limit:
                    raise exc('Line is too long.')

                start, self.offset = self.offset, end
                self.size -= size

                return self[start:end]
            else:
                if limit is not None and self.size > limit:
                    raise exc('Line is too long.')

            self._writer.send((yield))

    def skip(self, size):
        """skip() skips specified amount of bytes."""

        while self.size < size:
            self._writer.send((yield))

        self.size -= size
        self.offset += size

    def skipuntil(self, stop):
        """skipuntil() reads until `stop` bytes sequence."""
        assert isinstance(stop, bytes) and stop, \
            'bytes is required: {!r}'.format(stop)

        stop_len = len(stop)

        while True:
            stop_line = self.find(stop, self.offset)
            if stop_line >= 0:
                end = stop_line + stop_len
                self.size -= end - self.offset
                self.offset = end
                return
            else:
                self.size = 0
                self.offset = len(self) - 1

            self._writer.send((yield))

    def __bytes__(self):
        return bytes(self[self.offset:])
