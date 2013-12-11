import aiohttp
import asyncio
import re
import irc.handler
import irc.plugins

URL_PATTERN = re.compile(r'https?://.*?\s?$')
TITLE_PATTERN = re.compile(r'<title[^>]*>(?P<title>.*?)</title[^>]*>')


def get_url(s):
    return next(URL_PATTERN.finditer(s))


TITLE_MESSAGE = '\02Title on {host}{url}:\02 {title}'


def handle_url(bot, target, url):
    resp = yield from aiohttp.request('GET', url, loop=bot.loop)
    # TODO don't read the whole response
    body = yield from resp.read()
    title_match = next(TITLE_PATTERN.finditer(str(body)), None)
    if title_match:
        title = title_match.group(1)
        # TODO check for redirect
        bot.send_privmsg(target, TITLE_MESSAGE.format(host=resp.host, url=resp.url, title=title))


class UrlPlugin(irc.plugins.BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.url_handlers = []

    def add_handler(self, url_handler):
        self.url_handlers.append(url_handler)

    def remove_handler(self, url_handler):
        self.url_handlers.remove(url_handler)

    @irc.handler.message_handler
    def privmsg(self, bot, message):
        target = message.params[0]
        url_match = get_url(message.params[1])
        if url_match:
            url = url_match.group()
            for h in self.url_handlers:
                m = h.match(url)
                if m:
                    yield from h.handle(bot, target, m)
                    break
            else:
                yield from handle_url(bot, target, url)


class BaseUrlHandlerPlugin(irc.plugins.BasePlugin):
    dependencies = [UrlPlugin]

    def __init__(self, bot):
        super().__init__(bot)
        bot.plugins[UrlPlugin.__name__].add_handler(self)

    def match(self, url):
        raise NotImplementedError

    def handle(self, bot, target, match):
        raise NotImplementedError


Plugin = UrlPlugin