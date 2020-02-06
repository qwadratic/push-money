from decimal import Decimal

from mintersdk.sdk.deeplink import MinterDeeplink
from mintersdk.sdk.transactions import MinterSendCoinTx

from config import TESTNET
from providers.mscan import MscanAPI
from minter.utils import to_bip, to_pip

BASE_COIN = 'MNT' if TESTNET else 'BIP'


def calc_bip_values(balances, subtract_fee=True, base_coin=BASE_COIN):
    """
    Get BIP (MNT for testnet) equivalent for each coin balance
    If `subtract_fee`=True:
      - take coin conversion fee into account
      - balances less than conversion fee are considered zero

    :param balances: <dict>
        { 'BIP': '112233323144', 'CUSTOM': '21234325366' }
        as returned by CustomMinterAPI.get_balance('Mx...')

    :param subtract_fee: <bool> take into account coin conversion fee
    :param base_coin: <str>
    :return: { coin: <Decimal> BIP value }
    """

    result = {}
    for coin, balance in balances.items():
        result.setdefault(coin, {})
        if coin == base_coin:
            result[coin] = to_bip(balance)
            continue

        est_sell_response = MscanAPI.estimate_coin_sell(coin, balance, base_coin)
        will_get_pip, comm_pip = int(est_sell_response['will_get']), int(est_sell_response['commission'])
        if subtract_fee and int(balance) <= comm_pip:
            # ignore "dust" balances
            result[coin] = Decimal(0)
            continue
        will_get_pip = will_get_pip - to_pip(0.1) if subtract_fee else will_get_pip
        result[coin] = to_bip(will_get_pip)

    return result


def create_deeplink(to, value, coin=BASE_COIN):
    tx = MinterSendCoinTx(coin, to, value, nonce=None, gas_coin=coin)
    deeplink = MinterDeeplink(tx, data_only=True, base_url='minter:///tx')
    return deeplink.generate()
