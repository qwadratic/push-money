from mintersdk.sdk.transactions import MinterSendCoinTx, MinterSellCoinTx, MinterSellAllCoinTx, MinterBuyCoinTx, \
    MinterCreateCoinTx, MinterDeclareCandidacyTx, MinterDelegateTx, MinterUnbondTx, MinterRedeemCheckTx, \
    MinterSetCandidateOnTx, MinterSetCandidateOffTx, MinterEditCandidateTx, MinterMultiSendCoinTx

from config import TESTNET

MIN_RESERVE_BIP = 10000
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