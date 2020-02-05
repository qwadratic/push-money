import os

import dotenv


dotenv.load_dotenv()

LOCAL = bool(int(os.environ.get('LOCAL')))
TESTNET = bool(int(os.environ.get('TESTNET')))

SQLITE_DBNAME = 'pushmoney.sqlite'
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')

MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
