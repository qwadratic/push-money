import os

import dotenv


dotenv.load_dotenv()

DEV = bool(int(os.environ.get('DEV')))
TESTNET = bool(int(os.environ.get('TESTNET')))

DB_NAME = os.environ.get('{}DB_NAME'.format('DEV_' if DEV else ''))
DB_USER = os.environ.get('{}DB_USER'.format('DEV_' if DEV else ''))
APP_DATABASE = {
    'name': DB_NAME,
    'engine': 'peewee.PostgresqlDatabase',
    'user': DB_USER
}

GOOGLE_CLIENT_KEY_FILENAME = 'gclient-keys.json'
MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
GRATZ_API_KEY = os.environ.get('GRATZ_API_KEY')
UNU_API_KEY = os.environ.get('UNU_API_KEY')

SMTP_HOST = 'smtp-mail.outlook.com'
SMTP_PORT = 587
EMAIL_SENDER = "noreply@push.money"
EMAIL_PASS = os.environ.get('EMAIL_PASS')

GRATZ_OWNER_EMAIL = 'amperluxe@gmail.com'
DEV_EMAIL = 'ivan.d.kotelnikov@gmail.com'

ADMIN_PASS = os.environ.get('ADMIN_PASS')
SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT')
APP_SECRET_KEY = os.environ.get('APP_SECRET_KEY')
