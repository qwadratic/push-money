from config import TESTNET, MSCAN_URL
from minter.api import CustomMinterAPI
from minter.utils import to_bip, to_pip

BASE_COIN = 'MNT' if TESTNET else 'BIP'
API = CustomMinterAPI(MSCAN_URL)


def bip_value(balances, base_coin=BASE_COIN):
    """
    Calc total address balance in BIP (MNT for testnet)
        - ignores balances lower than exchange fee
        - take coin conversion fee into account
        - assume that conversion rate will not change while performing exchange transactions

    :param balances: <dict>
        { coin symbol, <str>: balance, pip <str> }
        as returned by CustomMinterAPI.get_balance('Mx...', convert=False)

    :param base_coin: <str>
    :return: <Decimal> balance of an address in BIP (MNT for testnet)
    """

    amount_pip = 0
    for coin, balance in balances.items():
        if coin == base_coin:
            amount_pip += int(balance)
        else:
            est_sell_response = API.estimate_coin_sell(coin, balance, base_coin)
            will_get_pip, comm_pip = int(est_sell_response['will_get']), int(est_sell_response['commission'])
            if int(balance) <= comm_pip:
                # ignore "dust" balances
                continue
            amount_pip += (will_get_pip - to_pip(0.1))
    return to_bip(amount_pip)
