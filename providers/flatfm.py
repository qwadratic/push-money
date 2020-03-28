import requests

from api.models import PushWallet
from providers.minter import send_coins

FLATFM_BASE_URL = 'https://flat.fm/api/'


def flatfm_top_up(wallet: PushWallet, amount, profile):
    profile = profile.strip()
    r = requests.post(f'{FLATFM_BASE_URL}/users/wallet/address', json={'user_id': profile})
    response = r.json()
    if 'address' not in response:
        return response.get('error', {}).get('reason', f'Flat.fm profile "{profile}" not found')

    result = send_coins(wallet, response['address'], amount, wait=True)
    if isinstance(result, str):
        return result

    return True
