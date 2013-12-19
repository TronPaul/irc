import unittest
import asyncio
import unittest.mock
import irc.client
import irc.messages
import irc.protocol
import irc.parser
import irc.codes
import tests.utils


class TestClient(unittest.TestCase):
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

    def test_register_on_connect(self):
        transport, _ = self.patch_connect()
        c = irc.client.IrcClient('example.com', 'TestNick', loop=self.loop)
        expected = [unittest.mock.call.write(irc.messages.Nick('TestNick').encode()),
                    unittest.mock.call.write(irc.messages.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(transport.write.call_args_list, expected)

    def test_register_with_password_on_connect(self):
        transport, _ = self.patch_connect()
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        expected = [unittest.mock.call.write(irc.messages.Pass('testpass').encode()),
                    unittest.mock.call.write(irc.messages.Nick('TestNick').encode()),
                    unittest.mock.call.write(irc.messages.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(transport.write.call_args_list, expected)

    def test_handle_ping(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.Ping(['12345']).encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        expected = unittest.mock.call.write(irc.messages.Pong(['12345']).encode())

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.loop.run_until_complete(c._read_handler)

        self.assertEquals(transport.mock_calls[-1], expected)

    def test_handle_rpl_welcome(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.RPL_WELCOME, ['hello']).encode())
        stream.feed_eof()

        self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.loop.run_until_complete(c._read_handler)

        self.assertTrue(c.registered)
        self.assertEquals(c.nick, 'TestNick')
        self.assertTrue(c.attempted_nick is None)

    def test_handle_err_nicknameinuse(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_NICKNAMEINUSE, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.loop.run_until_complete(c._read_handler)

        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Nick('TestNick_').encode()))
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_handle_passwdmismatch_raises_error(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_PASSWDMISMATCH, ['Bad Password']).encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)

        self.assertRaises(irc.codes.PasswordMismatchError, self.loop.run_until_complete, c._read_handler)

    def test_handle_erroneusnickname(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_ERRONEUSNICKNAME, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.loop.run_until_complete(c._read_handler)

        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Nick('TestNick_').encode()))
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_set_nickname_on_matching_nickname(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.Nick('TestNick', prefix='PrevNick!stuff@stuff').encode())
        stream.feed_eof()

        self.patch_connect(protocol=stream)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c.nick = 'PrevNick'
        c.attempted_nick = 'TestNick'
        task = c.start()
        self.loop.run_until_complete(task)

        self.assertEquals(c.nick, 'TestNick')
        self.assertTrue(c.attempted_nick is None)

    def test_quit(self):
        self.patch_connect()
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        start_task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        self.loop.run_until_complete(c.quit())
        tests.utils.run_briefly(self.loop)
        self.assertTrue(c._send_handler.cancelled())
        self.assertTrue(c._read_handler.cancelled())

    def test_privmsg(self):
        transport, _ = self.patch_connect()
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        start_task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        msg = irc.messages.PrivMsg('test', 'a msg')
        self.loop.run_until_complete(c.send_privmsg('test', 'a msg'))
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(msg.encode()))