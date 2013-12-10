import re
import aiohttp
import asyncio
import irc.plugins.url

IMGUR_PATTERN = re.compile(
    r'http://((www|i)\.)?imgur\.com/((?P<type>a|gallery)/)?(?P<id>[^\./]+)(?P<extension>\.[a-z]{3})?(/comment/(?P<comment_id>\d+)$)?')


class ImgurPlugin(irc.plugins.url.BaseUrlHandlerPlugin):
    def __init__(self, bot):
        super().__init__(bot)
        client_id = bot.config.get('imgur_client_id')
        if not client_id:
            raise irc.plugins.PluginLoadError
        self.client_id = client_id

    def match(self, url):
        match = IMGUR_PATTERN.match(url)
        return match

    @asyncio.coroutine
    def handle(self, bot, target, match):
        groups = match.groupdict()
        if groups['comment_id']:
            yield from comment(bot, target, groups['comment_id'], self.client_id, bot.loop)
        else:
            if not groups['type']:
                yield from image(bot, target, groups['id'], self.client_id, bot.loop)
            elif groups['type'] == 'a':
                yield from album(bot, target, groups['id'], self.client_id, bot.loop)
            elif groups['type'] == 'gallery':
                yield from gallery(bot, target, groups['id'], self.client_id, bot.loop)


@asyncio.coroutine
def comment(bot, target, id, client_id, loop):
    d = yield from imgur_data('comment', id, client_id, loop)
    bot.send_privmsg(target, 'imgur comment: \02<{author}>\02 {comment}'.format(**d))


@asyncio.coroutine
def image(bot, target, id, client_id, loop):
    print('image')
    d = yield from imgur_data('image', id, client_id, loop)
    d['title'] = d.get('title', 'No Title')
    d['animated'] = ' animated' if 'animated' in d else ''
    print('sending')
    bot.send_privmsg(target, 'imgur: \02{title}\02 - {width}x{height} {type}{animated}'.format(**d))


@asyncio.coroutine
def album(bot, target, id, client_id, loop):
    d = yield from imgur_data('album', id, client_id, loop)
    d['title'] = d.get('title', 'No Title')
    bot.send_privmsg(target, 'imgur: \02{title}\02 - {images_count} images'.format(**d))


@asyncio.coroutine
def gallery(bot, target, id, client_id, loop):
    d = yield from imgur_data('gallery', id, client_id, loop)
    d['title'] = d.get('title', 'No Title')
    if d['is_album']:
        bot.send_privmsg(target, 'imgur: \02{title}\02 - {images_count} images'.format(**d))
    else:
        d['animated'] = ' animated' if 'animated' in d else ''
        bot.send_privmsg(target, 'imgur: \02{title}\02 - {width}x{height} {type}{animated}'.format(**d))

@asyncio.coroutine
def imgur_data(type, id, client_id, loop):
    url = r'https://api.imgur.com/3/{0}/{1}.json'.format(type, id)
    headers = {'Authorization': 'Client-ID {0}'.format(client_id)}
    resp = yield from aiohttp.request('GET', url, headers=headers, loop=loop)
    data = yield from resp.read(decode=True)
    return data['data']


Plugin = ImgurPlugin