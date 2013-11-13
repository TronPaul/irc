import logging

DELIM = bytes((0o40,))
NUL = bytes((0o0,))
NL = b'\n'
CR = b'\r'
EOL = CR + NL

class ProtocolViolationError(Exception):
    pass

def irc_split(data):
    buf = data
    nick = None
    username = None
    host = None
    trailing = None
    command = None

    if buf.endswith(EOL):
        buf = buf[:-2]
    else:
        raise ProtocolViolationError

    if buf.startswith(b':'):
        try:
            prefix, buf = buf[1:].split(DELIM, 1)
            nick, prefix = prefix.split(b'!', 1)
            username, host = prefix.split('@', 1)    
        except ValueError:
            pass

    try:
        command, buf = buf.split(DELIM, 1)
    except ValueError:
        raise ProtocolViolationError('No command recieved: {msg}'.format(msg=data))

    if buf.startswith(b':'):
        params = [buf[1:]]
    else:
        try:
            buf, trailing = buf.split(DELIM + b':', 1)
        except ValueError:
            pass
        params = buf.split(DELIM)
        if trailing is not None:
            params.append(trailing)

    return (nick, username, host), command, params

def irc_unsplit(prefix, command, params):
    buf = b''
    if prefix:
        buf += b':' + prefix + DELIM
    buf += command + DELIM
    if params is None:
        pass
    if len(params) == 1:
        param = params[0]
        if DELIM in param:
            buf += b':' + param
        else:
            buf += param
    else:
        if params:
            rparams, trailing = params[:-1], params[-1]
            if rparams:
                buf += DELIM.join(rparams) + DELIM
            if trailing:
                buf += b':' + trailing
    return buf.strip() + EOL

X_DELIM = bytes((0o1,))
X_QUOTE = bytes((0o134,))
M_QUOTE = bytes((0o20,))

_low_level_quote_table = {
    NUL: M_QUOTE + b'0',
    NL: M_QUOTE + b'n',
    CR: M_QUOTE + b'r',
    M_QUOTE: M_QUOTE * 2
}

_low_level_dequote_table = {
    v: k for k, v in _low_level_quote_table.items()}

_ctcp_quote_table = {
    X_DELIM: X_QUOTE + b'a',
    X_QUOTE: X_QUOTE * 2
}

_ctcp_dequote_table = {
    v: k for k, v in _ctcp_quote_table.items()}

def _quote(string, table):
    cursor = 0
    buf = b''
    for pos, char in enumerate(string):
        if pos is 0:
            continue
        if char in table:
            buf += string[cursor:pos] + table[char]
            cursor = pos + 1
    buf += string[cursor:]
    return buf

def _dequote(string, table):
    cursor = 0
    buf = b''
    last_char = b''
    for pos, char in enumerate(string):
        if pos is 0:
            last_char = char
            continue
        if last_char + char in table:
            buf += string[cursor:pos] + table[char]
            cursor = pos + 1
        last_char = char

    buf += string[cursor:]
    return buf

def low_level_quote(string):
    return _quote(string, _low_level_quote_table)

def low_level_dequote(string):
    return _dequote(string, _low_level_dequote_table)

def ctcp_quote(string):
    return _quote(string, _ctcp_quote_table)

def ctcp_dequote(string):
    return _dequote(string, _ctcp_dequote_table)

class Prefix:
    def __init__(self, nick, username, host):
        self.nick = nick
        self.username = username
        self.host = host

    def encode(self):
        prefix = nick
        if username:
            prefix.append('!{1}'.format(username))
            if host:
                prefix.append('@{1}'.format(host))
        return prefix

class Message:
    def __init__(self, command, params, prefix=None):
        if not command:
            raise ValueError
        self.prefix = prefix
        self.command = command
        self.params = params

    def __repr__(self):
        return 'Message({prefix}, {command}, {params})'.format(prefix=self.prefix,
            command=self.command, params=self.params)

    def encode(self):
        prefix = bytes(self.prefix, 'utf-8') if self.prefix else None
        command = bytes(self.command, 'utf-8')
        params = [bytes(p, 'utf-8') for p in self.params] if self.params else self.params
        return irc_unsplit(prefix, command, params)

class MessageParser:
    def __call__(self, out, buf):
        while True:
            raw_data = yield from buf.readuntil(EOL)
            prefix, command, params = irc_split(raw_data)
            nick, username, host = irc_split_prefix(prefix)
            if params:
                params = DELIM.join(params)
                decoded = low_level_dequote(params)
                messages = decoded.split(X_DELIM)
                messages.reverse()

                odd = False
                extended_messages = []
                normal_messages = []

                while messages:
                    message = messages.pop()
                    if odd:
                        if message:
                            ctcp_decoded = ctcp_dequote(message)
                            split = ctcp_decoded.split(DELIM, 1)
                            tag = split[0]
                            data = None
                            if len(split) > 1:
                                data = split[1]
                            extended_messages.append((tag, data))
                    else:
                        if message:
                            normal_messages += filter(None, message.split(DELIM))
                    odd = not odd
            command = str(command, 'utf-8')
            normal_messages = [str(m, 'utf-8') for m in normal_messages]
            out.feed_data(Message(command, normal_messages, prefix=prefix))
