from mintersdk.sdk.wallet import MinterWallet

from api.models import PushWallet
from minter.tx import send_coin_tx
from minter.utils import to_bip
from providers.mscan import MscanAPI


def send_coins(wallet: PushWallet, to=None, amount=None):
    amount = float(amount)

    private_key = MinterWallet.create(mnemonic=wallet.mnemonic)['private_key']
    response = MscanAPI.get_balance(wallet.address)
    nonce = int(response['transaction_count']) + 1

    balance_bip = float(to_bip(response['balance']['BIP']))

    # если вдруг пришлют сумму без учета комиссии - не будем мучать ошибками)
    amount = amount - 0.01 if amount == balance_bip else amount
    if amount > balance_bip - 0.01:
        return False

    tx = send_coin_tx(private_key, 'BIP', amount, to, nonce)
    MscanAPI.send_tx(tx, wait=True)
    return True


def ensure_balance(address, required_pip):
    balance = MscanAPI.get_balance(address)['balance']
    balance_pip = balance['BIP']
    return int(balance_pip) >= int(required_pip)
