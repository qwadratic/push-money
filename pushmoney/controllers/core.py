from mintersdk.sdk.wallet import MinterWallet
from shortuuid import uuid

from minter.helpers import API, bip_value
from minter.utils import to_bip
from providers.currency_rates import bip_to_usdt, fiat_to_usd_rates
from pushmoney.models import Wallet


def generate_and_save_wallet():
    link_id = uuid()
    wallet = MinterWallet.create()
    w = Wallet.create(
        link_id=link_id,
        address=wallet['address'],
        mnemonic=wallet['mnemonic'])
    return w


def address_balance(address):
    balances = API.get_balance(address)['balance']
    amount_bip = bip_value(balances)
    amount_usd = bip_to_usdt(amount_bip)
    usd_rates = fiat_to_usd_rates()
    return {
        'balances': {coin: float(to_bip(bal)) for coin, bal in balances.items()},
        'bip_value': float(amount_bip),
        'fiat': {
            'USD': amount_usd,
            **{symbol: rate * amount_usd for symbol, rate in usd_rates.items()}
        }
    }
