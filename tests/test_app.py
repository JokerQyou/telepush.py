# coding: utf-8
import asyncio
from datetime import datetime
import hmac
import os
import shutil
import tempfile
import time
from unittest import mock
from urllib.parse import urlparse

import pytest
from _pytest.monkeypatch import MonkeyPatch

app = None


@pytest.fixture(scope='session', autouse=True)
def monkeysession(request):
    '''Patch `telegram` related network operations,
    so we don't actually send requests to Telegram during testing.
    FYI: https://github.com/pytest-dev/pytest/issues/363
    '''
    mpatch = MonkeyPatch()
    mpatch.setattr('telegram.Bot.set_webhook', lambda x, y: None)
    mpatch.setattr('telegram.Bot._validate_token', lambda x, y: True)
    mpatch.setattr('telegram.Bot.send_message', lambda *x, **y: None)
    yield mpatch
    mpatch.undo()


@pytest.yield_fixture(scope='module')
def event_loop(request):
    '''Async fixtures require an `event_loop` fixture.
    Ref: https://github.com/pytest-dev/pytest-asyncio/issues/68
    '''
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module', autouse=True)
# We don't want to actually load `.env` file during testing
@mock.patch('telepush.config.load_dotenv', new_callable=lambda: None)
async def fake_app_config(request):
    '''Setup and teardown function for this test module.
    Basically setup test env vars and a temporary folder for storing data.
    Also clean up after testing.
    '''
    tmpdir = tempfile.mkdtemp(prefix='telepush_test_')
    print('Data stored in {}'.format(tmpdir))
    os.environ.update(dict(
        TELEGRAM_BOT_TOKEN='123456789:ABCDefGHIIklmnOpQrsTUVWXyZ123456789',
        TELEGRAM_BOT_USERNAME='test_bot_username',
        WEBSITE_URL='http://local.test',
        SECRET_KEY='test_secret',
        QUART_DEBUG='1',
        DATABASE_FILE=os.path.join(tmpdir, 'telepush.db'),
        LOG_FILE=os.path.join(tmpdir, 'telepush.log'),
    ))
    global app
    from telepush.app import app

    # Currently `Quart.startup` and `Quart.cleanup` does not get called
    # during testing, so we call them manually
    await app.startup()

    yield app

    await app.cleanup()
    print('Removing {}'.format(tmpdir))
    shutil.rmtree(tmpdir)


@pytest.fixture
def client():
    return app.test_client()


@pytest.mark.asyncio
async def test_favicon(client):
    response = await client.get('/favicon.ico')
    assert response.status_code == 204
    assert b'' == await response.get_data()


@pytest.mark.asyncio
async def test_index(client):
    bot_username = app.config['TELEGRAM_BOT_USERNAME']
    response = await client.get('/')
    assert response.status_code == 200

    body = await response.get_data()
    assert b'https://telegram.org/js/telegram-widget.js?4' in body
    assert b'data-request-access="write"' in body
    assert bytes('data-telegram-login="{}"'.format(bot_username), 'utf-8') in body  # noqa E501
    assert b'data-auth-url="' in body


@pytest.mark.asyncio
async def test_login_invalid(client):
    assert 400 == (await client.get('/login')).status_code
    assert 400 == (await client.get('/login', query_string={
        'id': 12345,
        'auth_date': 1234567,
        'first_name': 'Alice',
        'hash': 'some fake string value',
    })).status_code
    assert 400 == (await client.get('/login', query_string={
        'id': 12345,
        'auth_date': 'illegal value for int type',
        'first_name': 'Alice',
        'hash': 'some fake string value',
    })).status_code
    # `/login` only accept GET requests
    assert 405 == (await client.post('/login')).status_code


@pytest.mark.asyncio
async def test_login_valid(client):
    auth_data = {
        'id': 12346,
        'auth_date': int(time.mktime(datetime.utcnow().timetuple())),
        'first_name': 'Bob',
    }
    kvs = sorted(['{}={}'.format(k, v) for k, v in auth_data.items()])
    mac = hmac.new(
        app.config['TELEGRAM_AUTH_SECRET'],
        bytes('\n'.join(kvs), 'utf-8'),
        'SHA256',
    )
    auth_data['hash'] = mac.hexdigest()

    response = await client.get('/login', query_string=auth_data)
    assert 302 == response.status_code
    assert '/dashboard' == response.location


@pytest.mark.asyncio
async def test_webhook_invalid(client):
    webhook_path = app.config['TELEGRAM_BOT_WEBHOOK_PATH']
    assert 400 == (await client.post(webhook_path)).status_code
    # TODO Test with more malformed request data

    # Webhook endpoint only accept POST requests
    assert 405 == (await client.get(webhook_path)).status_code


@pytest.mark.asyncio
async def test_webhook_valid(client):
    '''Send a valid webhook request
     to finish user registration (started by test_login_valid).
    This requires `test_login_valid` to have succeeded.
    '''
    webhook_path = app.config['TELEGRAM_BOT_WEBHOOK_PATH']
    bot_domain = urlparse(app.config['WEBSITE_URL']).netloc
    now = int(time.mktime(datetime.utcnow().timetuple()))
    data = {
        'update_id': 1,
        'message': {
            'message_id': 2,
            'from': {
                'id': 12346,
                'is_bot': False,
                'first_name': 'Bob',
                'language_code': 'en-us',
            },
            'chat': {
                'id': 12346,
                'first_name': 'Bob',
                'type': 'private',
            },
            'date': now,
            'connected_website': bot_domain
        },
    }
    response = await client.post(webhook_path, json=data)
    assert 200 == response.status_code


@pytest.mark.asyncio
async def test_send_invalid(client):
    # POST: Missing parameters
    assert 400 == (await client.post('/send', form={'key': '123'})).status_code
    assert 400 == (await client.post('/send', form={'text': '12'})).status_code
    # GET: Missing parameters
    assert 400 == (await client.get('/send', query_string={
        'key': '123',
    })).status_code
    assert 400 == (await client.get('/send', query_string={
        'text': '12',
    })).status_code

    # POST: Full parameters, but with invalid code
    assert 401 == (await client.post('/send', form={
        'key': '123',
        'text': 'this text should not be sent',
    })).status_code
    # GET: Full parameters, but with invalid code
    assert 401 == (await client.get('/send', query_string={
        'key': '123',
        'text': 'this text should not be sent',
    })).status_code


@pytest.mark.asyncio
async def test_send_valid(client):
    '''Send a valid `send` request to trigger message sending.
    This requires `test_webhook_send_valid` to have succeeded.
    '''
    # Well, the only way is to get sendkey directly from database...
    from pony.orm import db_session
    from telepush.models import User
    with db_session:
        sendkey = User.get(id=12346).key

    assert 200 == (await client.post('/send', form={
        'key': sendkey,
        'text': 'this text should be sent',
    })).status_code


@pytest.mark.asyncio
async def test_logout(client):
    response = await client.get('/logout')
    assert 302 == response.status_code
    assert '/' == response.location
