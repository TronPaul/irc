import unittest
import unittest.mock
import asyncio
import irc
import irc.parser
import irc.messages
import irc.handler
import irc_admin


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

        self.assertRaises(PermissionError, wrapped_func, b, irc.handler.Command('Nick', 'test', 'target', []))
        self.assertFalse(called)

    def test_wrapper_with_permissions(self):
        # TODO find better way to store called state
        global called
        called = False

        def func(*args, **kwargs):
            global called
            called = True

        wrapped_func = irc_admin.admin_command_handler(lambda x: True, func)
        self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        wf_task = asyncio.Task(wrapped_func(b, irc.handler.Command('Nick', 'test', 'target', [])), loop=self.loop)
        self.loop.run_until_complete(wf_task)
        self.assertTrue(called)

    def test_join(self):
        transport, _ = self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        join_task = irc_admin.join(b, irc.handler.Command('Nick', 'join', '#chan', ['#newchan']))
        self.loop.run_until_complete(join_task)
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Join('#newchan').encode()))

    def test_part(self):
        transport, _ = self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        part_task = irc_admin.part(b, irc.handler.Command('Nick', 'part', '#chan', ['#oldchan']))
        self.loop.run_until_complete(part_task)
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Part('#oldchan').encode()))

    def test_quit(self):
        transport, _ = self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        quit_task = irc_admin.quit(b, irc.handler.Command('Nick', 'quit', '#chan', []))
        self.loop.run_until_complete(quit_task)
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(irc.messages.Quit().encode()))

    def test_raw(self):
        transport, _ = self.patch_connect()
        b = irc.IrcBot('irc.example.com', 'TulipBot', loop=self.loop)
        start_task = asyncio.Task(b.start(), loop=self.loop)
        self.loop.run_until_complete(start_task)
        raw_task = irc_admin.raw(b, irc.handler.Command('Nick', 'raw', '#chan', ['PRIVMSG target the string baby']))
        self.loop.run_until_complete(raw_task)
        self.assertEquals(transport.mock_calls[-1], unittest.mock.call.write(b'PRIVMSG target the string baby\r\n'))
