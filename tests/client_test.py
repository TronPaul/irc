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

        self.transport = unittest.mock.Mock()
        self.protocol = unittest.mock.MagicMock()


        @asyncio.coroutine
        def gen():
            return self.transport, self.protocol

        self.connect_mock_config = {'return_value.__iter__.return_value': gen()}

        @asyncio.coroutine
        def empty():
            pass

        self.read_loop_mock_config = {'return_value': empty()}

    def tearDown(self):
        self.loop.close()
        self.transport = None
        self.protocol = None

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


    def test_register_on_connect(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        self.create_patch('irc.client.IrcClient._read_loop', **self.read_loop_mock_config)

        c = irc.client.IrcClient('example.com', 'TestNick', loop=self.loop)
        expected = [unittest.mock.call(irc.messages.Nick('TestNick').encode()),
                    unittest.mock.call(irc.messages.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_register_with_password_on_connect(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        self.create_patch('irc.client.IrcClient._read_loop', **self.read_loop_mock_config)

        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        expected = [unittest.mock.call(irc.messages.Pass('testpass').encode()),
                    unittest.mock.call(irc.messages.Nick('TestNick').encode()),
                    unittest.mock.call(irc.messages.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_handle_ping(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport
        expected = [unittest.mock.call(irc.messages.Pong(['12345']).encode())]

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.Ping(['12345']).encode())
        stream.feed_eof()

        read = asyncio.Task(c._read_loop(stream), loop=self.loop)
        asyncio.Task(c._send_loop(), loop=self.loop)
        self.loop.run_until_complete(read)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_handle_rpl_welcome(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.RPL_WELCOME, ['hello']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertTrue(c.registered)
        self.assertEquals(c.nick, 'TestNick')
        self.assertTrue(c.attempted_nick is None)

    def test_handle_err_nicknameinuse(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_NICKNAMEINUSE, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        read = asyncio.Task(c._read_loop(stream), loop=self.loop)
        asyncio.Task(c._send_loop(), loop=self.loop)
        self.loop.run_until_complete(read)

        self.transport.write.assert_called_once_with(irc.messages.Nick('TestNick_').encode())
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_handle_passwdmismatch_raises_error(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_PASSWDMISMATCH, ['Bad Password']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.assertRaises(irc.codes.PasswordMismatchError, self.loop.run_until_complete, task)

    def test_handle_erroneusnickname(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.RawMessage(irc.codes.ERR_ERRONEUSNICKNAME, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        read = asyncio.Task(c._read_loop(stream), loop=self.loop)
        asyncio.Task(c._send_loop(), loop=self.loop)
        self.loop.run_until_complete(read)

        self.transport.write.assert_called_once_with(irc.messages.Nick('TestNick_').encode())
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_set_nickname_on_matching_nickname(self):
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c.nick = 'PrevNick'
        c.attempted_nick = 'TestNick'

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.Nick('TestNick', prefix='PrevNick!stuff@stuff').encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
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
