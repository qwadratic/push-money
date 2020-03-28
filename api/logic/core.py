from decimal import Decimal

from mintersdk.sdk.wallet import MinterWallet
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from shortuuid import uuid as _uuid

from helpers.url import make_icon_url
from minter.helpers import calc_bip_values, to_pip, to_bip
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


def uuid():
    while True:
        link_id = _uuid()[:6]
        if PushWallet.get_or_none(link_id=link_id):
            continue
        return link_id


def generate_and_save_wallet(**kwargs):
    password = kwargs.pop('password', None)
    password_hash = pbkdf2_sha256.hash(password) if password is not None else None

    link_id = uuid()
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
        balances_bip = calc_bip_values(balances)

    bip_value_total = sum(balances_bip.values()) - Decimal(0.01)
    if bip_value_total < 0:
        bip_value_total = 0
    usd_value_total = bip_to_usdt(bip_value_total)
    usd_rates = fiat_to_usd_rates()
    return {
        'balance': {
            coin: {
                'value': float(to_bip(balances[coin])),
                'bip_value': float(bip_value),
                'usd_value': bip_to_usdt(bip_value)
            }
            for coin, bip_value in balances_bip.items()
        },
        'bip_value_total': float(bip_value_total),
        'usd_value_total': usd_value_total,
        'fiat_rates': {
            symbol: rate for symbol, rate in usd_rates.items()
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
    shops_top = ['resend', 'transfer-minter', 'biptophone'] + _top_shop_slugs + ['timeloop', 'unu', 'flatfm']
    certificates = {}
    categories = {
        # 'biptophone': {
        #     'title': {'ru': 'Связь', 'en': 'Communication'},
        #     'color': '#1FC3F7',
        #     'icon': db._app.config['BASE_URL'] + url_for('upload.icons', content_type='category', object_name='mobile'),
        # }
    }
    shops = {
        'biptophone': {
            'title': {'ru': 'Пополнить', 'en': 'Top Up'},
            'icon': make_icon_url('category', 'mobile'),
            'icon_fav': make_icon_url('category', 'mobile'),
            'inputs': [
                {'type': 'amount', 'param_name': 'amount'},
                {'type': 'phone', 'param_name': 'phone'}
            ]
        },
        'unu': {
            'title': {'ru': 'UNU Platform', 'en': 'UNU Platform'},
            'icon': make_icon_url('shop', 'unu'),
            'icon_fav': make_icon_url('shop', 'unu'),
            'inputs': [
                {'type': 'amount', 'param_name': 'amount'},
                {'type': 'email', 'param_name': 'email', 'placeholder': 'Unu.ru registration email'}
            ]
        },
        'flatfm': {
            'title': {'ru': 'flat.fm', 'en': 'flat.fm'},
            'icon': make_icon_url('shop', 'flatfm'),
            'icon_fav': make_icon_url('shop', 'flatfm'),
            'inputs': [
                {'type': 'amount', 'param_name': 'amount'},
                {'type': 'text', 'param_name': 'profile', 'placeholder': 'Flat.fm profile link, username or email'}
            ]
        },
        'timeloop': {
            'title': {'ru': 'Timeloop', 'en': 'Timeloop'},
            'icon': make_icon_url('shop', 'timeloop'),
            'icon_fav': make_icon_url('shop', 'timeloop'),
            'inputs': [{'type': 'amount', 'param_name': 'amount'}],
        },
        'bipgame': {
            'title': {'ru': 'Галактика Онлайн', 'en': 'Bipgame'},
            'icon': make_icon_url('shop', 'bipgame'),
            'icon_fav': make_icon_url('shop', 'bipgame'),
            'inputs': [{'type': 'amount', 'param_name': 'amount'}],
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
