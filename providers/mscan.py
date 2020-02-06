from config import MSCAN_APIKEY, TESTNET
from minter.api import CustomMinterAPI

MSCAN_URL = f'https://api.mscan.dev/{MSCAN_APIKEY}/{"test_node" if TESTNET else "node"}'
MscanAPI = CustomMinterAPI(MSCAN_URL)
