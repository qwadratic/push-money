from decimal import Decimal, getcontext, ROUND_HALF_DOWN

import requests
from mintersdk.sdk.wallet import MinterWallet

from api.models import PushWallet
from config import BIP2PHONE_API_KEY
from providers.mscan import MscanAPI
from minter.tx import send_coin_tx
from minter.helpers import to_bip, effective_balance

# BIP2PHONE_API_URL = 'https://biptophone.ru/api.php'
# requests to my proxy, because my server doesn't see API host :)
BIP2PHONE_API_URL = 'https://static.255.135.203.116.clients.your-server.de/api.php'
BIP2PHONE_PAYMENT_ADDRESS = 'Mx403b763ab039134459448ca7875c548cd5e80f77'

getcontext().prec = 6
getcontext().rounding = ROUND_HALF_DOWN


def mobile_top_up(wallet: PushWallet, phone=None, amount=None, confirm=True):
    if not confirm:
        return get_info()

    phone_reqs = get_tx_requirements(phone)
    if not phone_reqs:
        return f'Phone number {phone} not supported or invalid'

    response = MscanAPI.get_balance(wallet.address)
    balance = response['balance']
    balances_bip = effective_balance(balance)
    main_coin, main_balance_bip = max(balances_bip.items(), key=lambda i: i[1])
    balance_coin = to_bip(balance[main_coin])
    nonce = int(response['transaction_count']) + 1
    to_send = amount or balance_coin

    private_key = MinterWallet.create(mnemonic=wallet.mnemonic)['private_key']

    tx = send_coin_tx(
        private_key, main_coin, to_send, BIP2PHONE_PAYMENT_ADDRESS, nonce,
        payload=phone_reqs['payload'], gas_coin=main_coin)
    fee = to_bip(tx.get_fee()) if main_coin == 'BIP' \
        else to_bip(MscanAPI.estimate_tx_comission(tx.signed_tx)['commission'])
    min_topup = phone_reqs['min_bip_value'] + fee
    effective_topup = Decimal(to_send) - fee

    if balance_coin < to_send:
        return 'Not enough balance'
    if effective_topup < min_topup:
        return f"Minimal top-up: {min_topup} BIP"

    tx = send_coin_tx(
        private_key, main_coin, effective_topup, BIP2PHONE_PAYMENT_ADDRESS, nonce,
        payload=phone_reqs['payload'], gas_coin=main_coin)
    MscanAPI.send_tx(tx, wait=True)
    return True


def mobile_validate_normalize(phone):
    r = requests.post(BIP2PHONE_API_URL, data={'key1': BIP2PHONE_API_KEY, 'phone': phone, 'validation': 1})
    r.raise_for_status()
    data = r.json()
    return {'valid': bool(int(data['isvalid'])), 'phone': data['phone']}


def get_tx_requirements(phone):
    r = requests.post(BIP2PHONE_API_URL, data={'key1': BIP2PHONE_API_KEY, 'phone': phone, 'contact': 1})
    r.raise_for_status()
    data = r.json()
    if 'keyword' not in data:
        return None
    return {
        'payload': data['keyword'],
        'country': data['country'],
        'min_bip_value': Decimal(str(data['minbip']))
    }


def get_last_payment_status(phone):
    r = requests.post(BIP2PHONE_API_URL, data={'key1': BIP2PHONE_API_KEY, 'phone': phone, 'status': 1})
    r.raise_for_status()
    data = r.json()
    if 'success' not in data:
        return None
    return {
        'status': int(data['success']),
        'bip': Decimal(data.get('bip')),
        'rub': Decimal(data.get('amount')),
    }


def get_info():
    r = requests.post(BIP2PHONE_API_URL, data={'key1': BIP2PHONE_API_KEY, 'curs': 1})
    r.raise_for_status()
    data = r.json()
    return {'RUB': float(data['RUB']), 'limit_bip': float(data['LIMIT'])}
