from mintersdk.sdk.wallet import MinterWallet
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from shortuuid import uuid as _uuid

from minter.helpers import calc_bip_values
from minter.utils import to_bip
from providers.currency_rates import bip_to_usdt, fiat_to_usd_rates
from api.models import PushWallet
from providers.minter import send_coins
from providers.mscan import MscanAPI
from providers.biptophone import mobile_top_up


def uuid():
    while True:
        link_id = _uuid()[:6]
        if PushWallet.get_or_none(link_id=link_id):
            continue
        return link_id


def generate_and_save_wallet(sender, recipient, password):
    link_id = uuid()
    wallet = MinterWallet.create()
    w = PushWallet.create(
        link_id=link_id,
        address=wallet['address'],
        mnemonic=wallet['mnemonic'],
        sender=sender,
        recipient=recipient,
        password_hash=pbkdf2_sha256.hash(password) if password is not None else None)
    return w


def get_address_balance(address):
    balances = MscanAPI.get_balance(address)['balance']
    balances_bip = calc_bip_values(balances)
    bip_value_total = sum(balances_bip.values())
    usd_value_total = bip_to_usdt(bip_value_total)
    usd_rates = fiat_to_usd_rates()
    return {
        'balance': {
            coin: {
                'value': float(to_bip(balances[coin])),
                'bip_value': float(bip_value),
                'usd_value': bip_to_usdt(bip_value)
            }
            for coin, bip_value in balances_bip.items() if bip_value > 0
        },
        'bip_value_total': float(bip_value_total),
        'usd_value_total': usd_value_total,
        'fiat_rates': {
            symbol: rate for symbol, rate in usd_rates.items()
        }
    }


def spend_balance(wallet: PushWallet, option, **kwargs):
    spend_option_fns = {
        'mobile': mobile_top_up,
        'transfer-minter': send_coins
    }
    return spend_option_fns[option](wallet, **kwargs)


def get_spend_categories():
    # Пока что Mock
    #
    # Заметка по transfer/withdrawal
    # Конечное видение - разделить вывод и пересылку на две категории, но механика одна:
    #         выбор опции (карта|минтер|биток|qiwi и т. д.)
    #         ввод реквизитов
    #         магия
    # В случае withdraw - выбранные реквизиты запоминаются и закрепляются за юзером
    # В следующий раз при выборе withdraw эти реквизиты предлагаются автоматически
    # В случае transfer - деньги просто переводятся
    #   на этот случай на фронте есть доп. возможность - скопировать текущую ссылку на push
    #   (?) мб будет история и можно выбрать получателя из истории
    #
    # Пока что будем отдавать только transfer, чтобы никого не запутать

    top_categories = ['transfer', 'mobile', 'taxi', 'charity', 'lottery']
    other_categories = [
        'bills', 'services', 'food',
        'transport', 'offers', 'games',
        'fuel', 'gifts', 'entertainment'
    ]

    enabled_categories = ['transfer', 'mobile']
    enabled_options = ['transfer-minter']

    category_options = {
        'transfer': ['transfer-minter', 'transfer-card'],
    }
    return [
        {
            'category': category_name,
            'enabled': category_name in enabled_categories,
            'top': category_name in top_categories,
            'spend_options': [
                {
                    'option': option_name,
                    'enabled': option_name in enabled_options
                }
                for option_name in category_options.get(category_name, [])
            ]
        } for category_name in top_categories + other_categories
    ]
