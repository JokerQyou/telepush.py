# coding: utf-8
import asyncio
from datetime import datetime
import hmac
import random
import string
import time

from pony.orm import db_session
from quart import (
    g, Quart, redirect, render_template, request, session, url_for,
)
from telegram import Bot, ParseMode, Update

from .models import db, User

app = Quart(__name__)
app.config.from_object('telepush.config.Config')
bot = Bot(token=app.config['TELEGRAM_BOT_TOKEN'])
bot.set_webhook(
    app.config['WEBSITE_URL'] + app.config['TELEGRAM_BOT_WEBHOOK_PATH'],
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


def generate_sendkey():
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for i in range(64)
    )


async def send_message(chat_id, text, reply_to, parsemode):
    bot.sendMessage(
        chat_id, text,
        parse_mode=parsemode, reply_to_message_id=reply_to,
    )


@app.before_serving
async def create_db_pool():
    print('Setting up db_pool')
    db.bind(
        provider='sqlite',
        filename=app.config['DATABASE_FILE'],
        create_db=True,
    )
    db.generate_mapping(create_tables=True)
    g.db_pool = db


@app.after_serving
async def close_db_pool():
    db_pool = g.get('db_pool')
    if db_pool:
        print('Closing db_pool...')
        await g.db_pool.flush()
        await g.db_pool.disconnect()


@app.route('/')
async def index():
    '''Home page. Basically a static page with a login button.
    '''
    return await render_template('index.html')


@app.route('/login')
async def login():
    '''Login. Telegram authentication redirects here.
    '''
    if verify_telegram_auth(request.args):
        id = request.args['id']
        session['tg_id'] = id

        # If this is a new user, create record
        with db_session:
            user = User.get(id=id)
            if not user:
                user = User(id=id, first_name=request.args['first_name'])
        return redirect(url_for('view_dashboard'))
    else:
        return 'Auth failed', 400


@app.route('/logout')
async def logout():
    '''Logout'''
    session.pop('tg_id', None)
    return redirect(url_for('index'))


@app.route('/dashboard')
async def view_dashboard():
    '''Dashboard. User can view / reset sendkey, or logout.
    '''
    # Not logged in
    if not session.get('tg_id'):
        return redirect(url_for('index'))

    with db_session:
        user = User.get(id=session['tg_id'])
        if not user:
            # TODO Log with warning level, potential security breach
            return redirect(url_for('logout'))

    return await render_template(
        'dashboard.html',
        first_name=user.first_name,
        sendkey=user.key,
    )


@app.route(app.config['TELEGRAM_BOT_WEBHOOK_PATH'], methods=['POST'])
async def webhook():
    '''API endpoing for Telegram webhook.
    Telegram sends update messages to this endpoint.
    '''
    update = Update.de_json(await request.get_json(), bot)
    if not update:
        return 'No update', 400

    if update.message and update.message.connected_website:
        message = update.message
        with db_session:
            user = User.get(id=message.from_user.id)
            if user and not user.key:
                user.set(chat_id=message.chat.id, key=generate_sendkey())
                return 'Ok'
            else:
                return 'Hmmmm', 204

    return 'Ok'


@app.route('/send', methods=['POST', 'GET'])
async def send():
    '''API endpoint for sending a message via Telegram'''
    form = await request.form
    sendkey = form.get('key', request.args.get('key'))
    text = form.get('text', request.args.get('text'))

    if all([sendkey, text]):
        # Find `chat_id` by `sendkey`, and send `text` to it
        with db_session:
            user = User.get(key=sendkey)
            if not user:
                return 'No such user', 401

        asyncio.ensure_future(send_message(
            user.chat_id,
            text,
            None,
            ParseMode.MARKDOWN,
        ))
        return 'Ok'
    else:
        return 'Invalid send request', 400


@app.route('/favicon.ico')
async def favicon():
    '''Stub for favicon'''
    return '', 204
