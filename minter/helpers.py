from decimal import Decimal

from mintersdk.shortcuts import to_bip, to_pip
from mintersdk.sdk.deeplink import MinterDeeplink

from minter.consts import BASE_COIN, TX_TYPES, MIN_RESERVE_BIP
from minter.tx import estimate_custom_fee
from providers.nodeapi import NodeAPI


def find_gas_coin(balances, get_fee=False, payload=''):
    for coin, balance_pip in balances.items():
        tx_fee = estimate_custom_fee(coin, payload=payload)
        if not tx_fee:
            continue
        if to_bip(balance_pip) - tx_fee >= 0:
            return coin if not get_fee else (coin, tx_fee)
    return None if not get_fee else (None, None)


def effective_value(value, coin):
    tx_fee = estimate_custom_fee(coin)
    if tx_fee is None:
        return value
    if tx_fee >= value:
        return Decimal(0)
    return Decimal(value) - tx_fee


def effective_balance(balances):
    balances_bip = {}
    for coin, balance in balances.items():
        if coin == BASE_COIN:
            balances_bip[coin] = max(Decimal(0), to_bip(balance) - Decimal('0.01'))
            continue

        # ROUBLE WORKAROUND
        coin_info = NodeAPI.get_coin_info(coin)
        if coin_info['reserve_balance'] < to_pip(Decimal(MIN_RESERVE_BIP) + Decimal('0.01')):
            return {coin: Decimal(0)}

        est_sell_response = NodeAPI.estimate_coin_sell(coin, balance, BASE_COIN)
        will_get_pip, comm_pip = est_sell_response['will_get'], est_sell_response['commission']
        if int(balance) < int(comm_pip):
            continue
        will_get_pip = int(will_get_pip) - to_pip(0.01)
        if will_get_pip > 0:
            balances_bip[coin] = to_bip(will_get_pip)
    return balances_bip or {'BIP': Decimal(0)}


class TxDeeplink(MinterDeeplink):

    def __init__(self, tx, data_only=True, base_url=''):
        super().__init__(tx, data_only=data_only, base_url=base_url)

    @staticmethod
    def create(tx_type, **kwargs):
        kwargs.setdefault('nonce', 0)
        kwargs.setdefault('coin', 'BIP')
        kwargs.setdefault('gas_coin', BASE_COIN)
        data_only = kwargs.pop('data_only', True)
        tx = TX_TYPES[tx_type](**kwargs)
        return TxDeeplink(tx, data_only=data_only)

    @property
    def mobile(self):
        base_url = self.base_url
        self.base_url = 'minter:///tx'
        link = self.generate()
        self.base_url = base_url
        return link

    @property
    def web(self):
        base_url = self.base_url
        self.base_url = 'https://bip.to/tx'
        link = self.generate()
        self.base_url = base_url
        return link
