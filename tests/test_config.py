# coding: utf-8
import sys
print(sys.path)


def test_config_attrs():
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
