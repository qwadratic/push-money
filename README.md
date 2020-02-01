push.money API
==============


### Prerequisites

- nginx
- python 3.8.0
- virtualenv


### Install

1.  Clone this repo and move to project directory, then execute:

        $ make install

    This will create virtualenv and install all dependencies in it

2.  Create `.env` file in root project directory

    Sample `.env`:

        TESTNET = 0
        MSCAN_APIKEY = ... # API key for https://mscan.dev
        BIP2PHONE_API_KEY = ... # API key for https://biptophone.ru/apiuser.php

3.  Execute migration script:

        $ make migrate

    For now it just creates empty SQLite DB, but will be updated in future.


### Run

1.  For local development:

        $ make run dev

    Will run flask development server in "debug" mode on http://127.0.0.1:5000

2.  For server deployment:

        $ make run prod

    It will run UWSGI app (using `gunicorn`) listening on `http://127.0.0.1:8000` in background mode.
    Logs will be written to `gunicorn.log` file in root project directory.

    You can setup nginx reverse proxy pointing to this URL to make your app visible on the Internet.

    To stop UWSGI app, execute:

        $ make stop


### Usage

API is standalone product, which can be used in any frontend app.


### API

[API docs are available here](https://gist.github.com/eternalflow/f80b488516908f3e501f3989d66e0d08) (in Russian)
