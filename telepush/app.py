# coding: utf-8
import asyncio

import eliot
from pony.orm import db_session
from quart import (
    g, Quart, redirect, render_template, request, session, url_for,
)
from telegram import Bot, ParseMode, Update

from .models import db, User
from .utils import eliot_log, generate_sendkey, log, verify_telegram_auth

eliot.use_asyncio_context()

app = Quart(__name__)
app.config.from_object('telepush.config.Config')
eliot.to_file(open(app.config['LOG_FILE'], 'a'))

bot = Bot(token=app.config['TELEGRAM_BOT_TOKEN'])
bot.set_webhook(
    app.config['WEBSITE_URL'] + app.config['TELEGRAM_BOT_WEBHOOK_PATH'],
)


async def send_message(chat_id, text, reply_to, parsemode):
    '''Send a text message to given Telegram chat'''
    bot.sendMessage(
        chat_id, text,
        parse_mode=parsemode, reply_to_message_id=reply_to,
    )


@app.before_serving
async def create_db_pool():
    log(message_type='create_db_pool')
    db.bind(
        provider='sqlite',
        filename=app.config['DATABASE_FILE'],
        create_db=True,
    )
    db.generate_mapping(create_tables=True)
    g.db_pool = db


@app.after_serving
async def close_db_pool():
    log(message_type='enter close_db_pool')
    db_pool = g.get('db_pool')
    if db_pool:
        log(message_type='close_db_pool')
        await g.db_pool.flush()
        await g.db_pool.disconnect()


@app.route('/')
@eliot_log
async def index():
    '''Home page. Basically a static page with a login button.
    '''
    return await render_template('index.html')


@app.route('/login')
@eliot_log
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
@eliot_log
async def logout():
    '''Logout'''
    session.pop('tg_id', None)
    return redirect(url_for('index'))


@app.route('/dashboard')
@eliot_log
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
@eliot_log
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

    return 'Ok'


@app.route('/send', methods=['POST', 'GET'])
@eliot_log
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
                log(message_type='warn', error='User not found', key=sendkey, text=text)
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
