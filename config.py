import os

import dotenv


dotenv.load_dotenv()

LOCAL = bool(int(os.environ.get('LOCAL')))
TESTNET = bool(int(os.environ.get('TESTNET')))

SQLITE_DBNAME = 'pushmoney.sqlite'
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')

GOOGLE_CLIENT_KEY_FILENAME = 'gclient-keys.json'
MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
SENDPULSE_API_ID = os.environ.get('SENDPULSE_API_ID')
SENDPULSE_API_SECRET = os.environ.get('SENDPULSE_API_SECRET')

GRATZ_API_KEY = os.environ.get('GRATZ_API_KEY')
