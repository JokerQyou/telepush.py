# coding: utf-8
from datetime import datetime
import hmac
from importlib import reload
import os
import sys
import time
from unittest import mock

import pytest
from _pytest.monkeypatch import MonkeyPatch

from telepush.app import app


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


@pytest.fixture(scope='module', autouse=True)
# We don't want to actually load `.env` file during testing
@mock.patch('telepush.config.load_dotenv', new_callable=lambda: None)
def fake_app_config():
    os.environ.update(dict(
        TELEGRAM_BOT_TOKEN='123456789:ABCDefGHIIklmnOpQrsTUVWXyZ123456789',
        TELEGRAM_BOT_USERNAME='test_bot_username',
        WEBSITE_URL='http://local.test',
        SECRET_KEY='test_secret',
        QUART_DEBUG='1',
        DATABASE_FILE=':memory:'
    ))
    reload(sys.modules['telepush.config'])
    reload(sys.modules['telepush.app'])
    # We just reloaded the module, should also replace the `app` instance
    global app
    app = sys.modules['telepush.app'].app


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
    assert 301 == response.status_code
    assert '/dashboard' == response.location


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
    assert 400 == (await client.post('/send', form={
        'key': '123',
        'text': 'this text should not be sent',
    })).status_code
    # GET: Full parameters, but with invalid code
    assert 400 == (await client.get('/send', query_string={
        'key': '123',
        'text': 'this text should not be sent',
    })).status_code


@pytest.mark.asyncio
async def test_send_valid(client):
    assert 200 == (await client.post('/send', form={
        'key': '12345',
        'text': 'this text should be sent',
    })).status_code


@pytest.mark.asyncio
async def test_webhook_invalid(client):
    webhook_path = app.config['TELEGRAM_BOT_WEBHOOK_PATH']
    assert 400 == (await client.post(webhook_path)).status_code

    # Webhook endpoint only accept POST requests
    assert 405 == (await client.get(webhook_path)).status_code


@pytest.mark.asyncio
async def test_webhook_valid():
    pass


@pytest.mark.asyncio
async def test_logout(client):
    response = await client.get('/logout')
    assert 301 == response.status_code
    assert '/' == response.location
