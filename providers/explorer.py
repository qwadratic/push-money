import requests

from helpers.misc import retry

EXPLORER_BASE_URL = 'https://explorer-api.minter.network/api/v1'
DEFAULT_COIN_LIST = ["ROUBLE", "DICE", "TIME", "UNUCOIN", "PIZZA", "POPE"]


@retry((requests.HTTPError, requests.Timeout), tries=3, delay=0.2, backoff=3, default=DEFAULT_COIN_LIST)
def get_coins():
    return requests.get(f'{EXPLORER_BASE_URL}/coins').json()['data']


def get_custom_coin_symbols():
    return [coindata['symbol'] for coindata in get_coins() if coindata['symbol'] != 'BIP']
