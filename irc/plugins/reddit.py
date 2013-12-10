import re
import json
import datetime
import aiohttp
import irc.plugins.url


REDDIT_PATTERN = re.compile(r'http://((www|pay)\.)?reddit\.com(?P<path>/.*)$')

PATH_PATTERN = re.compile(r'/(?P<type>[^/]+)/(?P<target>[^?/]+)(/comments/(?P<long_id>(?P<post_id>[^/]+)/(?P<post_name>[^/]+)(/(?P<comment_id>[^/]+))?)?)?/?')


class RedditPlugin(irc.plugins.url.BaseUrlHandlerPlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def match(self, url):
        return REDDIT_PATTERN.match(url)

    def handle(self, bot, target, match):
        path_match = PATH_PATTERN.match(match.group('path'))
        if path_match:
            groups = path_match.groupdict()
            print(groups)
            if 'u' == groups['type'] or 'user' == groups['type']:
                yield from self.user(bot, target, groups['target'])
            elif 'r' == groups['type']:
                if groups['comment_id']:
                    yield from self.comment(bot, target, groups['long_id'])
                elif groups['post_id']:
                    yield from self.post(bot, target, groups['post_id'])
                else:
                    yield from self.subreddit(bot, target, groups['target'])
            else:
                yield from self.post(bot, target, match.group('path'))
        else:
            yield from self.post(bot, target, match.group('path'))

    def post(self, bot, target, id):
        url = 'http://www.reddit.com/comments/{0}.json'.format(id)
        resp = yield from aiohttp.request('GET', url, loop=bot.loop)
        body = yield from resp.read()
        data = json.loads(body.decode())
        post = data[0]['data']['children'][0]['data']
        d = {}
        d['nsfw'] = '[NSFW] ' if post['over_18'] else ''
        d['subreddit'] = post['subreddit']
        d['title'] = post['title']
        d['score'] = post['score']
        d['num_comments'] = post['num_comments']
        msg = '{nsfw}/r/{subreddit}: \02{title}\02 - \02{score}\02 Karma - \02{num_comments}\02 Comments'.format(**d)
        bot.send_privmsg(target, msg)

    def subreddit(self, bot, target, name):
        url = 'http://www.reddit.com/r/{0}/about.json'.format(name)
        resp = yield from aiohttp.request('GET', url, loop=bot.loop)
        body = yield from resp.read()
        data = json.loads(body.decode())
        sub = data['data']
        d = {}
        d['nsfw'] = '[NSFW] ' if sub.get('over_18') else ''
        d['url'] = sub['url']
        d['title'] = sub['title']
        d['subscribers'] = sub['subscribers']
        d['public_description'] = sub['public_description']
        msg = '{nsfw}{url}: \02{title}\02 - \02{subscribers} Subscribers - {public_description}'.format(**d)
        bot.send_privmsg(target, msg)

    def user(self, bot, target, username):
        url = 'http://www.reddit.com/user/{0}/about.json'.format(username)
        resp = yield from aiohttp.request('GET', url, loop=bot.loop)
        body = yield from resp.read()
        data = json.loads(body.decode())
        user = data['data']
        d = {}
        d['name'] = user['name']
        d['link_karma'] = user['link_karma']
        d['comment_karma'] = user['comment_karma']
        d['joined'] = datetime.datetime.utcfromtimestamp(user['created_utc']).strftime('%d %b %Y')
        msg = '\02{name}\02 - \02{link_karma}\02 Link Karma - \02{comment_karma}\02 Comment Karma - Joined {joined}'.format(**d)
        bot.send_privmsg(target, msg)

    def comment(self, bot, target, id):
        url = 'http://www.reddit.com/comments/{0}.json'.format(id)
        resp = yield from aiohttp.request('GET', url, params={'depth': 1}, loop=bot.loop)
        body = yield from resp.read()
        data = json.loads(body.decode())
        com = data[1]['data']['children'][0]['data']
        d = {}
        d['score'] = com['ups'] - com['downs']
        d['nsfw'] = '[NSFW] ' if com.get('over_18') else ''
        d['author'] = com['author']
        attrs = next(filter(None, ['Gilded' if com['gilded'] > 0 else '', 'Edited' if com['edited'] else '']), [])
        d['attributes'] = ', '.join(attrs) + ' ' if attrs else ''
        d['body'] = com['body']
        msg = '{nsfw}Comment by {author} \02{score}\02 Karma {attributes}- {body}'.format(**d)
        bot.send_privmsg(target, msg)


Plugin = RedditPlugin