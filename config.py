import os

import dotenv


dotenv.load_dotenv()

TESTNET = bool(int(os.environ.get('TESTNET')))

SQLITE_DBNAME = 'pushmoney.sqlite'

MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
BIP2PHONE_API_KEY = os.environ.get('BIP2PHONE_API_KEY')
