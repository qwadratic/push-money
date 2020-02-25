push.money API
==============


### Prerequisites

- Postgres 9.6
- nginx
- python 3.8.0
- virtualenv


### Install

1.  Clone this repo and move to project directory, then execute:

        $ make install

    This will create virtualenv and install all dependencies in it

2.  Create `.env` file in root project directory

    Sample `.env`:
        
        DB_USER = ...  # postgres db user
        DB_NAME = ...  # postgres db pass
  
        TESTNET = 0
        MSCAN_APIKEY = ... # API key for https://mscan.dev
        BIP2PHONE_API_KEY = ... # API key for https://biptophone.ru/apiuser.php
        GIFTERY_API_ID = ... # API client id for https://b2b.giftery.ru
        GIFTERY_API_SECRET = ... # API client secret for https://b2b.giftery.ru
        BIP_WALLET = ... # bip coin wallet to receive coins for giftery integration
        GRATZ_API_KEY = # API key for gratz certificates provider
        MAIL_PASS = # password for noreply@push.money

3.  Execute migration script:

        $ make migrate

    This will create all Postgres tables (assuming you configured PG properly)
    
    Also, when you change models - you should run this script, to apply changes in DB

### Run

1.  For local development:

        $ make run dev

    Will run flask development server in "debug" mode on http://127.0.0.1:8000

2.  For server deployment:

        $ make run prod

    It will run UWSGI app (using `gunicorn`) listening on `http://127.0.0.1:8000` in background mode with 4 workers at a time.
    
    Logs will be written to `gunicorn.log` file in root project directory.

    You should setup nginx reverse proxy pointing to this URL to make your app visible on the Internet.

    To stop WSGI app, execute:

        $ make stop


### Usage

Push Money API is standalone project, which can be used in any frontend app.

It is now used for https://yyy.cash and https://t.me/yyycashbot


### API

API docs are available at https://push.money/swagger

You can test every endpoint from your browser using "Try it out" button.
