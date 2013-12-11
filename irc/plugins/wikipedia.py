import json
import re
import aiohttp
import irc.plugins.url


WIKI_PATTERN = re.compile(r'http://(?P<site>[^\.]+)\.wikipedia\.org/wiki/(?P<page>[^#]+)')

TAG_PATTERN = re.compile(r'<[^>]+>')

PUNCT_PATTERN = re.compile(r'\s([.!,?]+)\s')

# noinspection PyTypeChecker
SPACE_PAGE_DICT = str.maketrans({c: '_' for c in '\t\r\n\f'})
# noinspection PyTypeChecker
SPACE_SNIP_DICT = str.maketrans({c: ' ' for c in ' \t\r\n\f'})


class WikipediaPlugin(irc.plugins.url.BaseUrlHandlerPlugin):
    def match(self, url):
        return WIKI_PATTERN.match(url)

    def handle(self, bot, target, match):
        page = match.group('page')
        site = match.group('site')
        url = r'https://{0}.wikipedia.org/w/api.php'.format(site)

        params = {
            'action': 'query',
            'format': 'json',
            'srsearch': page,
            'limit': 1,
            'list': 'search'
        }

        resp = yield from aiohttp.request('GET', url, params=params)
        data = yield from resp.read()
        data = json.loads(data.decode())
        if not data['query'] or not data['query']['search']:
            bot.send_privmsg(target, 'No results for {0}'.format(page))
        else:
            result = data['query']['search'][0]
            d = {}
            d['title'] = result['title']
            d['snippet'] = PUNCT_PATTERN.sub(r'\1 ', TAG_PATTERN.sub('', result['snippet']).translate(SPACE_SNIP_DICT))

            bot.send_privmsg(target, '\02{title}\02: {snippet}'.format(**d))

Plugin = WikipediaPlugin