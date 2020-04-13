from mintersdk import MinterHelper
from mintersdk.sdk.transactions import MinterSendCoinTx, MinterTx
from mintersdk.shortcuts import to_bip
from config import TESTNET

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
