import asyncio

def run_briefly(loop):
    @asyncio.coroutine
    def once():
        pass
    t = asyncio.Task(once(), loop=loop)
    loop.run_until_complete(t)
