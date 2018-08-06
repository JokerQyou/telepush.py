# Telepush.py

------
[![Build Status](https://travis-ci.com/JokerQyou/telepush.py.svg?branch=master)](https://travis-ci.com/JokerQyou/telepush.py)

An opensource version of the retired [ethbot service][ethbot_github]. Currently under development.

# Setup for development / debugging

- First of all you should get a domain name;
- Create a bot via Telegram [BotFather][botfather]
  - Get the bot token;
  - Set bot domain via [BotFather][botfather];
- Clone this project and setup environment
  - Setup Python 3 (>= 3.6) environment;
  - Install requirements: `pip install -r requirements.txt`;
  - Copy the sample config file `cp .env.example .env`;
  - Edit `.env` file, fill in your config values;
- Optionally you can run the test suite:
  - Install development requirements: `pip install -r requirements-dev.txt`;
  - Run tests: `pytest -v`;
- Start
  - `export QUART_APP=telepush.app:app`;
  - `quart run`
- Visit your domain and login with Telegram;

If you run this project on your local machine (e.g. when during development),
 you can use `localtunnel` or other alternatives to setup reverse proxy
 for your domain. [Serveo][serveo_website] is the recommended alternative.

## Notice

The above instructions are only for development / testing purpose.
Instructions for setting up a production instance will be available
 once the code is fully tested.
 (As you can see with `pytest --cov=telepush --cov-report=html`,
 the test coverage is not very high.)

# Contribute

Welcome. Please remember to write tests for added lines.

[ethbot_github]: https://github.com/JokerQyou/ethbot/
[botfather]: https://t.me/BotFather
[serveo_website]: https://serveo.net/