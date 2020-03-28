import hashlib

from api.models import PushWallet
from shortuuid import uuid

from minter.tx import estimate_payload_fee
from providers.minter import send_coins

TIMELOOP_ADDRESS = 'Mx3650064486380210127159872871912061022891'
BIPGAME_ADDRESS = 'Mxc938ac4123503aa691ff106ce98f732fae0f01b3'


def timeloop_top_up(wallet: PushWallet, amount):
    gift_code = uuid()
    h = hashlib.sha256()
    h.update(gift_code.encode('utf-8'))
    payload = h.hexdigest()

    amount_fact = amount - float(estimate_payload_fee(payload, bip=True))
    if amount_fact <= 0:
        return 'Amount is too low'

    result = send_coins(wallet, TIMELOOP_ADDRESS, amount_fact, payload=payload, wait=True)
    if isinstance(result, str):
        return result

    return {'link': f'https://timeloop.games/?gift={gift_code}'}


def bipgame_top_up(wallet: PushWallet, amount):
    gift_code = uuid()
    h = hashlib.sha256()
    h.update(gift_code.encode('utf-8'))
    payload = f'push:{h.hexdigest()}'

    amount_fact = amount - float(estimate_payload_fee(payload, bip=True))
    if amount_fact <= 0:
        return 'Amount is too low'

    result = send_coins(wallet, BIPGAME_ADDRESS, amount_fact, payload=payload, wait=True)
    if isinstance(result, str):
        return result

    return {'link': f'https://bipgame.io/public/push?gift={gift_code}'}
