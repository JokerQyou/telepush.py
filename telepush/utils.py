# coding: utf-8
from datetime import datetime
from functools import wraps
import hmac
import random
import string
import time

import eliot
from quart import current_app as app, url_for


def eliot_log(func):
    '''Decorate async view function so eliot logging is automatically done.
    You can also use `eliot.Message.log()` to do manual log
     inside decorated view function.
    This decorator should sit inside `.route()`, e.g.:
    @app.route('/')
    @eliot_log
    async def my_view():
        ...
    '''
    @wraps(func)
    async def wrapped_view_func():
        with eliot.start_action(
            action_type='serve {}'.format(url_for(func.__name__))
        ):
            return await func()

    return wrapped_view_func


def generate_sendkey():
    '''Generate a random string as sendkey.
    Currently the length is 64.
    '''
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for i in range(64)
    )


def verify_telegram_auth(auth_data):
    '''Verify if auth_data actually comes from Telegram.
    Ref: https://core.telegram.org/widgets/login#checking-authorization
    '''
    hash = auth_data.pop('hash', None)
    try:
        auth_date = int(auth_data.get('auth_date', 0))
        # Sorry, you are too late
        if time.mktime(datetime.utcnow().timetuple()) - auth_date > 86400:
            return False
    except Exception:
        return False

    kvs = sorted(['{}={}'.format(k, v) for k, v in auth_data.items()])
    mac = hmac.new(
        app.config['TELEGRAM_AUTH_SECRET'],
        bytes('\n'.join(kvs), 'utf-8'),
        'SHA256',
    )
    return mac.hexdigest() == hash


def log(*args, **kw):
    '''Simple wrapper around `eliot.Message`.
    Currently supports log only.
    '''
    return eliot.Message.log(*args, **kw)
