import unittest
import irc.protocol as protocol

class TestSplit(unittest.TestCase):
    def test_split_without_EOL_raises_error(self):
        self.assertRaises(protocol.ProtocolViolationError,
            protocol.irc_split, b'NICK Test')

    def test_split_without_command_raises_error(self):
        self.assertRaises(protocol.ProtocolViolationError,
            protocol.irc_split, b':prefix \r\n')

    def test_split_without_prefix(self):
        prefix, command, params = protocol.irc_split(b'NICK Test\r\n')
        self.assertEquals(prefix.nick, b'')
        self.assertEquals(command, b'NICK')
        self.assertEquals(params, [b'Test'])

    def test_split(self):
        prefix, command, params = protocol.irc_split(b':Wiz NICK Test\r\n')
        self.assertEquals(prefix.nick, b'Wiz')
        self.assertEquals(command, b'NICK')
        self.assertEquals(params, [b'Test'])

    def test_split_with_long_param(self):
        prefix, command, params = protocol.irc_split(b':Wiz USER Test Test arg :A Real Name\r\n')
        self.assertEquals(prefix.nick, b'Wiz')
        self.assertEquals(command, b'USER')
        self.assertEquals(params, [b'Test', b'Test', b'arg', b'A Real Name'])

class TestUnsplit(unittest.TestCase):
    def test_unsplit_without_prefix(self):
        raw = protocol.irc_unsplit(None, b'NICK', [b'Test'])
        self.assertEquals(raw, b'NICK Test\r\n')

    def test_unsplit(self):
        raw = protocol.irc_unsplit(b'Wiz', b'NICK', [b'Test'])
        self.assertEquals(raw, b':Wiz NICK Test\r\n')

    def test_unsplit_with_long_param(self):
        raw = protocol.irc_unsplit(b'Wiz', b'USER', [b'Test', b'Test', b'arg', b'a long one'])
        self.assertEquals(raw, b':Wiz USER Test Test arg :a long one\r\n')
