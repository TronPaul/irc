import unittest
import irc.command

class CommandTest(unittest.TestCase):
    def test_make_params_parser(self):
        parse_fn = irc.command.make_params_parser('test', ['a', 'b', 'c'])
        params = parse_fn('a b c')
        self.assertEquals(params.a, 'a')
        self.assertEquals(params.b, 'b')
        self.assertEquals(params.c, 'c')

    def test_make_params_parser_with_list_last(self):
        parse_fn = irc.command.make_params_parser('test', ['a', 'b', 'c'], irc.command.LastParamType.list_)
        params = parse_fn('a b c d e')
        self.assertEquals(params.a, 'a')
        self.assertEquals(params.b, 'b')
        self.assertEquals(params.c, ['c', 'd', 'e'])

    def test_make_params_parser_with_string_last(self):
        parse_fn = irc.command.make_params_parser('test', ['a', 'b', 'c'], irc.command.LastParamType.string)
        params = parse_fn('a b c d e')
        self.assertEquals(params.a, 'a')
        self.assertEquals(params.b, 'b')
        self.assertEquals(params.c, 'c d e')

    def test_incorrect_param_length_raises_parse_error(self):
        parse_fn = irc.command.make_params_parser('test', ['a', 'b', 'c'])
        self.assertRaises(irc.command.ParamsParseError, parse_fn, 'a b c d e')
