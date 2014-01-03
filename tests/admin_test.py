import unittest
import unittest.mock
import asyncio
import irc.bot
import irc.command
import irc.parser
import irc.messages
import irc_admin
import tests.utils


class TestAdmin(unittest.TestCase):
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

    def test_wrapper_no_permissions(self):
        global called
        called = False

        def func(*args, **kwargs):
            global called
            called = True

        wrapped_func = irc_admin.admin_command_handler(lambda x: False, func)
        self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)

        self.assertRaises(PermissionError, wrapped_func, b, irc.command.Command('Nick', 'test', 'target', []))
        self.assertFalse(called)

    def test_wrapper_with_permissions(self):
        # TODO find better way to store called state
        global called
        called = False

        @asyncio.coroutine
        def func(*args, **kwargs):
            global called
            called = True

        wrapped_func = irc_admin.admin_command_handler(lambda x: True, func)
        self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        wf_task = asyncio.Task(wrapped_func(b, irc.command.Command('Nick', 'test', 'target', [])), loop=self.loop)
        self.loop.run_until_complete(wf_task)
        self.assertTrue(called)

    def test_join(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.PrivMsg('#channel', ';join #newchan', prefix='admin!Admin@admin.com').encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        b.config['OWNER'] = 'admin'
        irc_admin.Admin(b)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        self.loop.run_until_complete(b._read_handler)
        self.loop.run_until_complete(asyncio.Task(b.tasks.join(), loop=self.loop))
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Join('#newchan').encode()))

    def test_part(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.PrivMsg('#channel', ';part #oldchan', prefix='admin!Admin@admin.com').encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        b.config['OWNER'] = 'admin'
        irc_admin.Admin(b)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        self.loop.run_until_complete(b._read_handler)
        self.loop.run_until_complete(asyncio.Task(b.tasks.join(), loop=self.loop))
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Part('#oldchan').encode()))

    def test_quit(self):
        transport, _ = self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        quit_task = irc_admin.quit(b, irc.command.Command('Nick', 'quit', '#chan', []))
        self.loop.run_until_complete(quit_task)
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Quit().encode()))

    def test_raw(self):
        stream = irc.parser.StreamProtocol(loop=self.loop)
        stream.feed_data(irc.messages.PrivMsg('#channel', ';raw PRIVMSG target the string baby', prefix='admin!Admin@admin.com').encode())
        stream.feed_eof()

        transport, _ = self.patch_connect(protocol=stream)
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        b.config['OWNER'] = 'admin'
        irc_admin.Admin(b)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        self.loop.run_until_complete(b._read_handler)
        self.loop.run_until_complete(asyncio.Task(b.tasks.join(), loop=self.loop))
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(b'PRIVMSG target the string baby\r\n'))
