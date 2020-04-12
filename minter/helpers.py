from decimal import Decimal

from mintersdk import MinterConvertor
from mintersdk.sdk.deeplink import MinterDeeplink
from mintersdk.sdk.transactions import MinterSendCoinTx, MinterSellCoinTx, MinterSellAllCoinTx, MinterBuyCoinTx, \
    MinterCreateCoinTx, MinterDeclareCandidacyTx, MinterDelegateTx, MinterUnbondTx, MinterRedeemCheckTx, \
    MinterSetCandidateOnTx, MinterSetCandidateOffTx, MinterEditCandidateTx, MinterMultiSendCoinTx

from config import TESTNET
from providers.mscan import MscanAPI

BASE_COIN = 'MNT' if TESTNET else 'BIP'
TX_TYPES = {
    'send':	MinterSendCoinTx,
    'sell': MinterSellCoinTx,
    'sellall': MinterSellAllCoinTx,
    'buy': MinterBuyCoinTx,
    'mint': MinterCreateCoinTx,
    'declare': MinterDeclareCandidacyTx,
    'delegate': MinterDelegateTx,
    'unbond': MinterUnbondTx,
    'redeem': MinterRedeemCheckTx,
    'on': MinterSetCandidateOnTx,
    'off': MinterSetCandidateOffTx,
    'edit': MinterEditCandidateTx,
    'multisig': NotImplemented,
    'multisend': MinterMultiSendCoinTx,
}


def to_pip(bip):
    return MinterConvertor.convert_value(bip, 'pip')


def to_bip(pip):
    return MinterConvertor.convert_value(pip, 'bip')


def effective_balance(balances):
    balances_bip = {}
    for coin, balance in balances.items():
        if coin == BASE_COIN:
            balances_bip[coin] = to_bip(balance) - Decimal(0.01)
            continue
        est_sell_response = MscanAPI.estimate_coin_sell(coin, balance, BASE_COIN)
        will_get_pip, comm_pip = est_sell_response['will_get'], est_sell_response['commission']
        if int(balance) < int(comm_pip):
            continue
        will_get_pip = int(will_get_pip) - to_pip(0.01)
        if will_get_pip > 0:
            balances_bip[coin] = to_bip(will_get_pip)
    return balances_bip or {'BIP': Decimal(0)}


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
        # result.setdefault(coin, {})
        if coin == base_coin:
            result[coin] = to_bip(balance)
            continue

        # !!! TMP disable custom coin support

        # est_sell_response = MscanAPI.estimate_coin_sell(coin, balance, base_coin)
        # will_get_pip, comm_pip = int(est_sell_response['will_get']), int(est_sell_response['commission'])
        # if subtract_fee and int(balance) <= comm_pip:
        #     # ignore "dust" balances
        #     result[coin] = Decimal(0)
        #     continue
        # will_get_pip = will_get_pip - to_pip(0.1) if subtract_fee else will_get_pip
        # result[coin] = to_bip(will_get_pip)

    return result


class TxDeeplink(MinterDeeplink):

    def __init__(self, tx, data_only=True, base_url=''):
        super().__init__(tx, data_only=data_only, base_url=base_url)

    @staticmethod
    def create(tx_type, **kwargs):
        kwargs.setdefault('nonce', None)
        kwargs.setdefault('coin', 'BIP')
        kwargs.setdefault('gas_coin', BASE_COIN)
        tx = TX_TYPES[tx_type](**kwargs)
        return TxDeeplink(tx)

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
