import unittest
import unittest.mock
import asyncio
import irc.bot
import irc.messages
import irc.handler
import irc.protocol
import irc.parser
import irc.codes
import tests.utils


class TestBot(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    def create_patch(self, name, **config):
        patcher = unittest.mock.patch(name, **config)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def patch_connect(self, transport=None, protocol=None):
        if not transport:
            transport = unittest.mock.Mock()
        if not protocol:
            protocol = irc.parser.StreamProtocol(loop=self.loop)

        @asyncio.coroutine
        def gen(*args):
            return transport, protocol

        self.create_patch('irc.client._connect', new=gen)
        return transport, protocol

    def test_valid_command(self):
        b = irc.bot.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        self.assertTrue(b.valid_command(irc.messages.PrivMsg('test', ';command thing')))

    def test_invalid_command(self):
        b = irc.bot.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        self.assertFalse(b.valid_command(irc.messages.PrivMsg('test', 'command thing')))

    def test_non_nick_destination(self):
        b = irc.bot.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        self.assertEquals(b.destination(irc.handler.Command('OtherNick', 'test', '#channel', [])), '#channel')

    def test_nick_destination(self):
        b = irc.bot.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        b.attempted_nick = None
        b.nick = 'TulipBot'
        self.assertEquals(b.destination(irc.handler.Command('OtherNick', 'test', 'TulipBot', [])), 'OtherNick')

    def test_handle_welcome(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.RPL_WELCOME, ['abc']).encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        b = irc.bot.IrcBot('irc.example.com', 'TulipBot', loop=self.loop, config={'STARTING_CHANNELS': ['a', 'b']})
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        self.loop.run_until_complete(b._read_handler)
        tests.utils.run_briefly(self.loop)

        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Join('b').encode()))
        self.assertEquals(transport.mock_calls[-2], unittest.mock.call.write(irc.messages.Join('a').encode()))