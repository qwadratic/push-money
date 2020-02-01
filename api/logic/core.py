from mintersdk.sdk.wallet import MinterWallet
from shortuuid import uuid

from minter.helpers import calc_bip_values
from minter.api import API
from minter.utils import to_bip
from providers.currency_rates import bip_to_usdt, fiat_to_usd_rates
from api.models import PushWallet
from providers.minter import send_all_coins
from providers.mobile import mobile_top_up


def generate_and_save_wallet():
    link_id = uuid()
    wallet = MinterWallet.create()
    w = PushWallet.create(
        link_id=link_id,
        address=wallet['address'],
        mnemonic=wallet['mnemonic'])
    return w


def get_address_balance(address):
    balances = API.get_balance(address)['balance']
    balances_bip = calc_bip_values(balances)
    bip_value_total = sum(bal['bip_value'] for bal in balances_bip.values())
    usd_value_total = bip_to_usdt(bip_value_total)
    usd_rates = fiat_to_usd_rates()
    return {
        'address': address,
        'balance': {
            coin: {
                'value': float(to_bip(bal['pip'])),
                'bip_value': float(bal['bip_value']),
                'usd_value': bip_to_usdt(bal['bip_value'])
            }
            for coin, bal in balances_bip.items() if bal['bip_value'] > 0
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
        'transfer-minter': send_all_coins
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
