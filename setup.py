from distutils.core import setup

setup(
    name='irc',
    version='0.0.1',
    packages=['irc'],
    py_modules=['irc_admin'],
    url='https://github.com/TronPaul/irc',
    license='',
    author='Mark McGuire',
    author_email='',
    description='Irc library using aysncio',
    requires=['asyncio', 'enum34']
)
