from decimal import Decimal

from config import TESTNET, MSCAN_URL
from minter.api import CustomMinterAPI
from minter.utils import to_bip, to_pip

BASE_COIN = 'MNT' if TESTNET else 'BIP'
API = CustomMinterAPI(MSCAN_URL)


def calc_bip_values(balances, base_coin=BASE_COIN):
    """
    Set BIP (MNT for testnet) equivalent for each coin balance
    Take coin conversion fee into account
    Balances less than conversion fee are considered zero

    :param balances: <dict>
        { 'BIP': '112233323144', 'CUSTOM': '21234325366' }
        as returned by CustomMinterAPI.get_balance('Mx...')

    :param base_coin: <str>
    :return: {
        'BIP': {'pip': '112233323144', 'bip_value': Decimal(...)},
        'CUSTOM': {'pip': '21234325366', 'bip_value': Decimal(...)}
    }
    """

    result = {}
    for coin, balance in balances.items():
        result.setdefault(coin, {})
        result[coin]['pip'] = balance
        if coin == base_coin:
            result[coin]['bip_value'] = to_bip(balance)
            continue

        est_sell_response = API.estimate_coin_sell(coin, balance, base_coin)
        will_get_pip, comm_pip = int(est_sell_response['will_get']), int(est_sell_response['commission'])
        if int(balance) <= comm_pip:
            # ignore "dust" balances
            result[coin]['bip_value'] = Decimal(0)
            continue
        result[coin]['bip_value'] = to_bip(will_get_pip - to_pip(0.1))

    return result
