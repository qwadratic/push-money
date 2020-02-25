import requests

from api.models import PushWallet
from config import UNU_API_KEY
from providers.minter import send_coins

UNU_BASE_URL = 'https://unu.ru/api'


def unu_top_up(wallet: PushWallet, amount, email=None):
    if not email:
        return 'Email not specified'

    r = requests.post(UNU_BASE_URL, data={
        'api_key': UNU_API_KEY,
        'action': 'get_minter_wallet',
        'email': email
    })
    r.raise_for_status()
    response = r.json()

    if response['errors']:
        return response['errors']

    result = send_coins(wallet, response['wallet'], amount, wait=True)
    if isinstance(result, str):
        return result

    return True
