from mintersdk.sdk.transactions import MinterSendCoinTx

from minter.helpers import BASE_COIN
from minter.utils import to_bip


def send_coin_tx(pk, coin, value, to, nonce, gas_coin=BASE_COIN, payload=None):
    value = to_bip(value) if isinstance(value, str) else value
    tx = MinterSendCoinTx(coin, to, value, nonce=nonce, gas_coin=gas_coin, payload=payload)
    tx.sign(pk)
    return tx
