from mintersdk.sdk.transactions import MinterSendCoinTx

from minter.helpers import BASE_COIN
from minter.utils import to_bip


def send_coin_tx(pk, coin, value, to, nonce, gas_coin=BASE_COIN):
    value = to_bip(value) if isinstance(str, value) else value
    tx = MinterSendCoinTx(coin, to, value, nonce=nonce, gas_coin=gas_coin)
    tx.sign(pk)
    return tx
