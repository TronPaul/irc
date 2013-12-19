import unittest
import unittest.mock
import asyncio
import irc
import irc.parser
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
        called = False

        def func(*args, **kwargs):
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