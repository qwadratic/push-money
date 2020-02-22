import os

import dotenv


dotenv.load_dotenv()

DEV = bool(int(os.environ.get('DEV')))
TESTNET = bool(int(os.environ.get('TESTNET')))

DB_NAME = os.environ.get('{}DB_NAME'.format('DEV_' if DEV else ''))
DB_USER = os.environ.get('{}DB_USER'.format('DEV_' if DEV else ''))

GOOGLE_CLIENT_KEY_FILENAME = 'gclient-keys.json'
MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
SENDPULSE_API_ID = os.environ.get('SENDPULSE_API_ID')
SENDPULSE_API_SECRET = os.environ.get('SENDPULSE_API_SECRET')
GIFTERY_API_ID = os.environ.get('GIFTERY_API_ID')
GIFTERY_API_SECRET = os.environ.get('GIFTERY_API_SECRET')

GRATZ_API_KEY = os.environ.get('GRATZ_API_KEY')

SMTP_HOST = 'smtp-mail.outlook.com'
SMTP_PORT = 587
EMAIL_SENDER = "noreply@push.money"
EMAIL_PASS = os.environ.get('EMAIL_PASS')

GRATZ_OWNER_EMAIL = 'amperluxe@gmail.com'
DEV_EMAIL = 'ivan.d.kotelnikov@gmail.com'