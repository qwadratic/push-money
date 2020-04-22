from config import MSCAN_APIKEY, TESTNET, NODE_API, FUNFASY_PROJECT_ID, FUNFASY_PROJECT_SECRET
from minter.api import CustomMinterAPI

MSCAN_URL = f'https://api.mscan.dev/{MSCAN_APIKEY}/{"test_node" if TESTNET else "node"}'
FUNFASY_URL = 'https://mnt.funfasy.dev/v0/'
NodeAPI = CustomMinterAPI(MSCAN_URL if NODE_API == 'mscan' else FUNFASY_URL, headers={
    'X-Project-Id': FUNFASY_PROJECT_ID,
    'X-Project-Secret': FUNFASY_PROJECT_SECRET
})
