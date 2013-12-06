DELIM = bytes((0o40,))
NUL = bytes((0o0,))
NL = b'\n'
CR = b'\r'
EOL = CR + NL


class ProtocolViolationError(Exception):
    def __init__(self, raw):
        self.raw = raw


def split(raw):
    buf = raw
    prefix = None
    trailing = None

    if buf.endswith(EOL):
        buf = buf[:-2]
    else:
        raise ProtocolViolationError(raw)

    if buf.startswith(b':'):
        try:
            prefix, buf = buf[1:].split(DELIM, 1)
        except ValueError:
            pass

    try:
        command, buf = buf.split(DELIM, 1)
    except ValueError:
        raise ProtocolViolationError('No command recieved: {msg}'.format(msg=raw))

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

    return prefix, command, params


def split_prefix(prefix):
    nick = None
    username = None
    host = None

    try:
        nick, prefix = prefix.split('!', 1)
    except ValueError:
        pass

    try:
        username, host = prefix.split('@', 1)
    except ValueError:
        pass

    return nick, username, host


def unsplit(prefix_raw, command, params):
    buf = b''
    if prefix_raw:
        buf += b':' + prefix_raw + DELIM
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


def split_message(raw):
    prefix, command, params = split(raw)
    prefix = str(prefix, 'utf-8') if prefix else None
    command = str(command, 'utf-8')
    params = [str(p, 'utf-8') for p in params]
    return RawMessage(command, params, prefix=prefix)


class RawMessage:
    def __init__(self, command, params, prefix=None):
        if not command:
            raise ValueError
        self.prefix = prefix
        self.nick, self.username, self.host = (split_prefix(prefix) if prefix
                                               else (None, None, None))
        self.command = command
        self.params = params

    def __repr__(self):
        return 'Message({prefix}, {command}, {params})'.format(prefix=self.prefix,
                                                               command=self.command, params=self.params)

    def encode(self):
        prefix = bytes(self.prefix, 'utf-8') if self.prefix else None
        command = bytes(self.command, 'utf-8')
        params = [bytes(p, 'utf-8') for p in self.params] if self.params else self.params
        return unsplit(prefix, command, params)


class MessageParser:
    def __call__(self, out, buf):
        while True:
            raw_data = yield from buf.readuntil(EOL)
            out.feed_data(split_message(raw_data))
