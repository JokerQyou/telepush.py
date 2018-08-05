# coding: utf-8
from hashlib import sha256
import os

from dotenv import load_dotenv

load_dotenv()


class Config(object):
    '''Application configuration'''
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_BOT_USERNAME = os.getenv('TELEGRAM_BOT_USERNAME')
    WEBSITE_URL = os.getenv('WEBSITE_URL')
    SECRET_KEY = os.getenv('SECRET_KEY')
    TELEGRAM_BOT_WEBHOOK_PATH = '/' + TELEGRAM_BOT_TOKEN.rsplit(':', 1)[-1]
    TELEGRAM_AUTH_SECRET = sha256(bytes(TELEGRAM_BOT_TOKEN, 'utf-8')).digest()
    DATABASE_FILE = os.getenv('DATABASE_FILE')
    DEBUG = os.getenv('QUART_DEBUG', False)

    if DEBUG:
        from warnings import warn
        warn(
            'Running in DEBUG mode!'
            ' Please unset QUART_DEBUG environment variable'
            ' if you are running a production instance.'
        )
