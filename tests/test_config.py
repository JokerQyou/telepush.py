# coding: utf-8
from importlib import reload
import os
import sys
import tempfile

import pytest


@pytest.fixture(scope='module', autouse=True)
def fake_env_vars(request):
    tmpdir = tempfile.gettempdir()  # We don't actually create any file
    os.environ.update(dict(
        TELEGRAM_BOT_TOKEN='123456789:ABCDefGHIIklmnOpQrsTUVWXyZ123456789',
        TELEGRAM_BOT_USERNAME='test_bot_username',
        WEBSITE_URL='http://local.test',
        SECRET_KEY='test_secret',
        DATABASE_FILE=os.path.join(tmpdir, 'telepush.db'),
        LOG_FILE=os.path.join(tmpdir, 'telepush.log'),
    ))


def test_config_attrs(monkeypatch):
    '''Test Config object.
    It should contain all the following fields.
    '''
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    from telepush.config import Config
    assert hasattr(Config, 'TELEGRAM_BOT_TOKEN')
    assert hasattr(Config, 'TELEGRAM_BOT_USERNAME')
    assert hasattr(Config, 'WEBSITE_URL')
    assert hasattr(Config, 'SECRET_KEY')
    assert hasattr(Config, 'TELEGRAM_BOT_WEBHOOK_PATH')
    assert hasattr(Config, 'TELEGRAM_AUTH_SECRET')
    assert hasattr(Config, 'DEBUG')
    assert hasattr(Config, 'DATABASE_FILE')
    assert hasattr(Config, 'LOG_FILE')


def test_config_debug_warn(monkeypatch):
    '''Test Config object with QUART_DEBUG env var set.
    It should warn about running in DEBUG mode.
    '''
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    os.environ['QUART_DEBUG'] = 'yes'
    with pytest.warns(UserWarning, match=r'Running in DEBUG mode!.+'):
        reload(sys.modules['telepush.config'])
