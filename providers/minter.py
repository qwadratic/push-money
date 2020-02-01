from mintersdk.sdk.wallet import MinterWallet

from api.models import PushWallet
from minter.api import API
from minter.helpers import calc_bip_values
from minter.tx import send_coin_tx
from minter.utils import to_bip


def send_all_coins(wallet: PushWallet, to=None):
    private_key = MinterWallet.create(mnemonic=wallet.mnemonic)['private_key']
    response = API.get_balance(wallet.address)
    nonce = int(response['transaction_count']) + 1
    balances_bip = calc_bip_values(response['balance'], subtract_fee=False)

    txs_sent = 0
    for coin, bal in balances_bip.items():
        if bal['bip_value'] <= 0.01:
            continue
        tx = send_coin_tx(private_key, coin, bal['pip'], to, nonce, gas_coin=coin)
        comm = API.estimate_tx_comission(tx.signed_tx)['commission']
        to_send_bip = to_bip(int(bal['pip']) - int(comm))
        tx = send_coin_tx(private_key, coin, to_send_bip, to, nonce, gas_coin=coin)
        API.send_tx(tx, wait=True)
        txs_sent += 1
        nonce += 1
    return txs_sent > 0
