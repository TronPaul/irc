import unittest
import asyncio
import unittest.mock
import irc.client
import irc.commands
import irc.protocol
import irc.parser
import irc.codes


class TestClient(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

        self.transport = unittest.mock.Mock()
        self.protocol = unittest.mock.Mock()

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

    def test_register_on_connect(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        self.create_patch('irc.client.IrcClient._read_loop', **self.read_loop_mock_config)

        c = irc.client.IrcClient('example.com', 'TestNick', loop=self.loop)
        expected = [unittest.mock.call(irc.commands.Nick('TestNick').encode()),
                    unittest.mock.call(irc.commands.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_register_with_password_on_connect(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        self.create_patch('irc.client.IrcClient._read_loop', **self.read_loop_mock_config)

        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        expected = [unittest.mock.call(irc.commands.Pass('testpass').encode()),
                    unittest.mock.call(irc.commands.Nick('TestNick').encode()),
                    unittest.mock.call(irc.commands.User('TestNick', 'TestNick', 'tulip-irc', 'TestNick').encode())]

        task = asyncio.Task(c.start(), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_handle_ping(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport
        expected = [unittest.mock.call(irc.commands.Pong(['12345']).encode())]

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.commands.Ping(['12345']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertEquals(self.transport.write.call_args_list, expected)

    def test_handle_rpl_welcome(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.Message(irc.codes.RPL_WELCOME, ['hello']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)
        self.assertTrue(c._registered)
        self.assertEquals(c.nick, 'TestNick')
        self.assertTrue(c.attempted_nick is None)

    def test_handle_err_nicknameinuse(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.Message(irc.codes.ERR_NICKNAMEINUSE, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)

        self.transport.write.assert_called_once_with(irc.commands.Nick('TestNick_').encode())
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_handle_passwdmismatch_raises_error(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.Message(irc.codes.ERR_PASSWDMISMATCH, ['Bad Password']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.assertRaises(irc.codes.PasswordMismatchError, self.loop.run_until_complete, task)

    def test_handle_erroneusnickname(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.protocol.Message(irc.codes.ERR_ERRONEUSNICKNAME, ['TestNick', 'Nickname in use']).encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)

        self.transport.write.assert_called_once_with(irc.commands.Nick('TestNick_').encode())
        self.assertEquals(c.attempted_nick, 'TestNick_')

    def test_set_nickname_on_matching_nickname(self):
        self.create_patch('irc.client.IrcClient._connect', **self.connect_mock_config)
        c = irc.client.IrcClient('example.com', 'TestNick', password='testpass', loop=self.loop)
        c._transport = self.transport
        c.nick = 'PrevNick'
        c.attempted_nick = 'TestNick'

        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.commands.Nick('TestNick', prefix='PrevNick!stuff@stuff').encode())
        stream.feed_eof()

        task = asyncio.Task(c._read_loop(stream), loop=self.loop)
        self.loop.run_until_complete(task)

        self.assertEquals(c.nick, 'TestNick')
        self.assertTrue(c.attempted_nick is None)
