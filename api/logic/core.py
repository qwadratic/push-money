from decimal import Decimal

from mintersdk.sdk.wallet import MinterWallet
from passlib.handlers.pbkdf2 import pbkdf2_sha256

from helpers.misc import truncate, uuid
from helpers.url import make_icon_url
from minter.helpers import to_pip, to_bip, effective_balance, effective_value, BASE_COIN
from providers.currency_rates import bip_to_usdt, fiat_to_usd_rates
from api.models import PushWallet, Category, Shop
from providers.flatfm import flatfm_top_up
from providers.gift import gift_buy
from providers.giftery import giftery_buy
from providers.gratz import gratz_buy
from providers.minter import send_coins
from providers.mscan import MscanAPI
from providers.biptophone import mobile_top_up
from providers.timeloop import timeloop_top_up, bipgame_top_up
from providers.unu import unu_top_up
from providers.currency_rates import bip_price


def generate_and_save_wallet(**kwargs):
    password = kwargs.pop('password', None)
    password_hash = pbkdf2_sha256.hash(password) if password is not None else None

    link_id = uuid(unique_for_model=PushWallet, model_param='link_id')
    wallet = MinterWallet.create()
    return PushWallet.create(
        link_id=link_id,
        address=wallet['address'],
        mnemonic=wallet['mnemonic'],
        password_hash=password_hash, **kwargs)


def get_address_balance(address, virtual=None):
    if virtual:
        balances = {'BIP': virtual}
        balances_bip = {'BIP': Decimal(to_bip(virtual))}
    else:
        balances = MscanAPI.get_balance(address)['balance']
        balances_bip = effective_balance(balances)

    main_coin, main_balance_bip = max(balances_bip.items(), key=lambda i: i[1])
    bip_value_total = truncate(float(main_balance_bip), 4)

    usd_value_total = truncate(bip_to_usdt(bip_value_total), 4)
    usd_rates = fiat_to_usd_rates()
    local_fiat = 'RUB'
    local_fiat_value = truncate(usd_value_total * usd_rates[local_fiat], 4)
    coin_value = truncate(float(to_bip(balances[main_coin])), 4)
    coin_value = effective_value(coin_value, main_coin)
    return {
        'balance': {
            'coin': main_coin,
            'value': bip_value_total if main_coin == BASE_COIN else coin_value,
            'bip_value': bip_value_total,
            'usd_value': usd_value_total,
            'local_fiat': local_fiat,
            'local_fiat_value': local_fiat_value
        },
        'fiat_rates': {
            symbol: rate for symbol, rate in usd_rates.items()
            if symbol in ['UAH', 'USD', 'RUB']
        }
    }


def push_resend(
        wallet,
        new_password=None, sender=None, recipient=None, amount=None,
        virtual=None):
    if not amount:
        return 'Amount should be >0'
    virtual_balance = str(to_pip(amount)) if virtual else None
    new_wallet = generate_and_save_wallet(
        sender=sender, recipient=recipient, new_password=new_password,
        virtual_balance=virtual_balance, sent_from=wallet.link_id)
    if not virtual:
        result = send_coins(wallet, new_wallet.address, amount, wait=True)
        if isinstance(result, str):
            return result
    return {'new_link_id': new_wallet.link_id}


def spend_balance(wallet: PushWallet, slug, confirm=True, **kwargs):
    spend_option_fns = {
        'mobile': mobile_top_up,
        'transfer-minter': send_coins,
        'resend': push_resend,
        'unu': unu_top_up,
        'timeloop': timeloop_top_up,
        'bipgame': bipgame_top_up,
        'flatfm': flatfm_top_up
    }
    fn = spend_option_fns.get(slug)
    if slug not in ['transfer-minter', 'resend', 'timeloop', 'unu', 'bipgame', 'flatfm']:
        kwargs['confirm'] = confirm

    # im genius
    if 'gift' in slug:
        fn = gift_buy
        kwargs['product'] = slug.split('-')[1]
    if 'gratz' in slug:
        fn = gratz_buy
        kwargs['product'] = slug.split('-')[1]
    if 'giftery' in slug:
        fn = giftery_buy
        kwargs['product'] = slug.split('-')[1]

    if not fn:
        return 'Spend option is not supported yet'
    return fn(wallet, **kwargs)


def get_spend_list():
    _top_shop_names = ['Яндекс.Еда', 'Перекресток', 'okko.tv']
    _top_shops = [s for s in Shop.select(Shop.id, Shop.name).where(Shop.name.in_(_top_shop_names))]
    _top_shop_slugs = [s.slug for s in _top_shops]
    shops_top = ['resend', 'transfer-minter', 'biptophone'] + _top_shop_slugs + ['timeloop', 'bipgame', 'unu', 'flatfm']
    certificates = {
        'games': {
            'timeloop': {
                'price_type': 'custom',
                'inputs': [{'type': 'amount', 'param_name': 'amount'}]
            },
            'bipgame': {
                'price_type': 'custom',
                'inputs': [{'type': 'amount', 'param_name': 'amount'}]
            }
        },
        'online': {
            'unu': {
                'price_type': 'custom',
                'inputs': [
                    {'type': 'amount', 'param_name': 'amount'},
                    {'type': 'email', 'param_name': 'email', 'placeholder': 'Unu.ru registration email', 'suggest_last': True}
                ]
            },
            'flatfm': {
                'price_type': 'custom',
                'inputs': [
                    {'type': 'amount', 'param_name': 'amount'},
                    {'type': 'text', 'param_name': 'profile', 'placeholder': 'Flat.fm username', 'suggest_last': True}
                ]
            }
        },
        'mobile': {
            'biptophone': {
                'price_type': 'custom',
                'inputs': [
                    {'type': 'amount', 'param_name': 'amount'},
                    {'type': 'phone', 'param_name': 'phone', 'suggest_last': True}
                ]
            }
        }
    }
    categories = {
        'mobile': {
            'title': {'ru': 'Связь', 'en': 'Communication'},
            'color': '#1FC3F7',
            'icon': make_icon_url('category', 'mobile'),
            'icon_fav': make_icon_url('category', 'mobile'),
        }
    }
    shops = {
        'biptophone': {
            'title': {'ru': 'Пополнить', 'en': 'Top Up'},
            'icon': make_icon_url('category', 'mobile'),
            'icon_fav': make_icon_url('category', 'mobile'),
            'color': '#1FC3F7'
        },
        'unu': {
            'title': {'ru': 'UNU Platform', 'en': 'UNU Platform'},
            'icon': make_icon_url('shop', 'unu_fav'),
            'icon_fav': make_icon_url('shop', 'unu_fav'),
            'color': '#5C28B3'
        },
        'flatfm': {
            'title': {'ru': 'flat.fm', 'en': 'flat.fm'},
            'icon': make_icon_url('shop', 'flatfm_fav'),
            'icon_fav': make_icon_url('shop', 'flatfm_fav')
        },
        'timeloop': {
            'title': {'ru': 'Timeloop', 'en': 'Timeloop'},
            'icon': make_icon_url('shop', 'timeloop_fav'),
            'icon_fav': make_icon_url('shop', 'timeloop_fav'),
        },
        'bipgame': {
            'title': {'ru': 'Галактика Онлайн', 'en': 'Bipgame'},
            'icon': make_icon_url('shop', 'bipgame_fav'),
            'icon_fav': make_icon_url('shop', 'bipgame_fav')
        }
    }
    bip_coin_price = bip_price()

    for category in Category.select().where(~Category.slug % '%,%'):
        cat_shops = category.shops.where(Shop.active & ~Shop.deleted)
        if not cat_shops:
            continue
        categories[category.slug] = {
            'title': {'ru': category.title, 'en': category.title_en},
            'color': '#' + (category.display_color or ''),
            'icon': category.icon_url,
        }
        for shop in cat_shops:
            if not shop.products.count():
                continue
            certificates.setdefault(category.slug, {})
            certificates[category.slug].setdefault(shop.slug, [])
            shop_repr = shop.api_repr
            if not shop_repr:
                continue
            certificates[category.slug][shop.slug] = shop_repr
            shops[shop.slug] = {
                'title': {'ru': shop.name, 'en': shop.name},
                'icon': shop.icon_url,
            }
            if shop.slug in _top_shop_slugs:
                shops[shop.slug]['icon_fav'] = shop.icon_url + '_fav'

    return {
        'shops_top': shops_top,
        'certificates': certificates,
        'categories': categories,
        'shops': shops,
        'bip_coin_price': bip_coin_price
    }
