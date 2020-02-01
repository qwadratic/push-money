import os

import dotenv


dotenv.load_dotenv()

TESTNET = bool(int(os.environ.get('TESTNET')))

SQLITE_DBNAME = 'pushmoney.sqlite'
MSCAN_APIKEY = os.environ.get('MSCAN_APIKEY')
MSCAN_URL = f'https://api.mscan.dev/{MSCAN_APIKEY}/{"test_node" if TESTNET else "node"}'
