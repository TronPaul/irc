import unittest
import irc.protocol as protocol

class TestSpliteMessage(unittest.TestCase):
    def test_split_message_without_EOL_raises_error(self):
        self.assertRaises(protocol.ProtocolViolationError,
            protocol.split_message, b'NICK Test')

    def test_split_message_without_command_raises_error(self):
        self.assertRaises(protocol.ProtocolViolationError,
            protocol.split_message, b':prefix \r\n')

    def test_split_without_prefix(self):
        message = protocol.split_message(b'NICK Test\r\n')
        self.assertTrue(message.prefix is None)
        self.assertTrue(message.nick is None)
        self.assertTrue(message.username is None)
        self.assertTrue(message.host is None)
        self.assertEquals(message.command, 'NICK')
        self.assertEquals(message.params, ['Test'])

    def test_split_with_nick_prefix(self):
        message = protocol.split_message(b':Wiz NICK Test\r\n')
        self.assertEquals(message.prefix, 'Wiz')
        self.assertTrue(message.nick is None)
        self.assertTrue(message.username is None)
        self.assertTrue(message.host is None)
        self.assertEquals(message.command, 'NICK')
        self.assertEquals(message.params, ['Test'])

    def test_split_with_long_param(self):
        message = protocol.split_message(b':Wiz USER Test Test arg :A Real Name\r\n')
        self.assertEquals(message.prefix, 'Wiz')
        self.assertTrue(message.nick is None)
        self.assertTrue(message.username is None)
        self.assertTrue(message.host is None)
        self.assertEquals(message.command, 'USER')
        self.assertEquals(message.params, ['Test', 'Test', 'arg', 'A Real Name'])

class TestUnsplit(unittest.TestCase):
    def test_unsplit_without_prefix(self):
        raw = protocol.unsplit(None, b'NICK', [b'Test'])
        self.assertEquals(raw, b'NICK Test\r\n')

    def test_unsplit(self):
        raw = protocol.unsplit(b'Wiz', b'NICK', [b'Test'])
        self.assertEquals(raw, b':Wiz NICK Test\r\n')

    def test_unsplit_with_long_param(self):
        raw = protocol.unsplit(b'Wiz', b'USER', [b'Test', b'Test', b'arg', b'a long one'])
        self.assertEquals(raw, b':Wiz USER Test Test arg :a long one\r\n')
