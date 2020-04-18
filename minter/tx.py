from mintersdk import MinterHelper
from mintersdk.sdk.transactions import MinterSendCoinTx, MinterTx
from mintersdk.sdk.wallet import MinterWallet
from mintersdk.shortcuts import to_bip
from config import TESTNET
from providers.mscan import MscanAPI

BASE_COIN = 'MNT' if TESTNET else 'BIP'


def send_coin_tx(pk, coin, value, to, nonce, gas_coin=BASE_COIN, payload=''):
    to = to.strip()
    value = to_bip(value) if isinstance(value, str) else value
    tx = MinterSendCoinTx(coin, to, value, nonce=nonce, gas_coin=gas_coin, payload=payload)
    tx.sign(pk)
    return tx


def estimate_payload_fee(payload, bip=False):
    fee_pip = MinterHelper.pybcmul(
        len(bytes(payload, encoding='utf-8')) * MinterTx.PAYLOAD_COMMISSION,
        MinterTx.FEE_DEFAULT_MULTIPLIER)
    return to_bip(fee_pip) if bip else fee_pip


def estimate_custom_fee(coin):
    w = MinterWallet.create()
    tx = send_coin_tx(w['private_key'], coin, 0, w['address'], 1, gas_coin=coin)
    return to_bip(MscanAPI.estimate_tx_commission(tx.signed_tx)['commission'])
