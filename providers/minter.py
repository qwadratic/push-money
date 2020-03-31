from mintersdk.sdk.wallet import MinterWallet

from api.models import PushWallet
from minter.tx import send_coin_tx, estimate_payload_fee
from minter.helpers import to_bip
from providers.mscan import MscanAPI


def send_coins(wallet: PushWallet, to=None, amount=None, payload='', wait=True):
    private_key = MinterWallet.create(mnemonic=wallet.mnemonic)['private_key']
    response = MscanAPI.get_balance(wallet.address)
    nonce = int(response['transaction_count']) + 1

    balance_bip = float(to_bip(response['balance']['BIP']))

    payload_fee = float(estimate_payload_fee(payload, bip=True)) if payload else 0
    tx_fee = payload_fee + 0.01

    # если в обычной пересылке пришлют сумму без учета комиссии - не будем мучать ошибками
    amount = amount - tx_fee if amount == balance_bip and not payload else amount

    if amount > balance_bip - tx_fee:
        return 'Not enough balance'

    tx = send_coin_tx(private_key, 'BIP', amount, to, nonce, payload=payload)
    MscanAPI.send_tx(tx, wait=wait)
    return True


def get_balance(address, coin='BIP', bip=True):
    balance = MscanAPI.get_balance(address)['balance']
    balance_pip = balance[coin]
    return float(to_bip(balance_pip)) if bip else balance_pip


def ensure_balance(address, required_pip):
    balance_pip = get_balance(address, 'BIP', bip=False)
    return int(balance_pip) >= int(required_pip)


def get_first_transaction(address):
    tx = MscanAPI.get_transactions(f"tags.tx.to='{address[2:]}'", limit=1)
    if not tx:
        return None
    return tx[0]['tags']['tx.from']
