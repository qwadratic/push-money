from decimal import Decimal

from mintersdk.sdk.wallet import MinterWallet
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from shortuuid import uuid as _uuid

from minter.helpers import calc_bip_values
from minter.utils import to_bip, to_pip
from providers.currency_rates import bip_to_usdt, fiat_to_usd_rates
from api.models import PushWallet
from providers.gift import gift_buy, gift_product_list
from providers.giftery import giftery_buy
from providers.gratz import gratz_buy, gratz_product_list
from providers.minter import send_coins
from providers.mscan import MscanAPI
from providers.biptophone import mobile_top_up
from providers.timeloop import timeloop_top_up, bipgame_top_up
from providers.unu import unu_top_up


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


def spend_balance(wallet: PushWallet, option, confirm=True, **kwargs):
    spend_option_fns = {
        'mobile': mobile_top_up,
        'transfer-minter': send_coins,
        'resend': push_resend,
        'unu': unu_top_up,
        'timeloop': timeloop_top_up,
        'bipgame': bipgame_top_up
    }
    fn = spend_option_fns.get(option)
    if option not in ['transfer-minter', 'resend', 'timeloop', 'unu']:
        kwargs['confirm'] = confirm

    # im genius
    if 'gift' in option:
        fn = gift_buy
        kwargs['product'] = option.split('-')[1]
    if 'gratz' in option:
        fn = gratz_buy
        kwargs['product'] = option.split('-')[1]
    if 'giftery' in option:
        fn = giftery_buy
        kwargs['product'] = option.split('-')[1]

    if not fn:
        return 'Spend option is not supported yet'
    return fn(wallet, **kwargs)


def get_spend_categories():
    # все еще mock, рано создавать абстрактную модель
    standalone_options = [
        'transfer-minter', 'resend', 'mobile', 'unu', 'timeloop']

    gratz_products, gratz_test_product = gratz_product_list()
    gift_products, gift_test_product = gift_product_list()

    # так делать норм, пока категории не пересекаются
    product_tree = {**gratz_products, **gift_products}

    return {
        'others': standalone_options,
        'certificates': product_tree,
        'test': [gratz_test_product, gift_test_product]
    }


def get_spend_list():
    return {
        'others': ['transfer-minter', 'resend', 'b2ph', 'unu', 'timeloop'],
        'certificates': {
            'travel': {
                'Каршеринг BelkaCar': [
                    {
                        'slug': 'giftery-13103',
                        'brief': 'Вы платите только за минуты пользования машиной. Расходы на бензин, парковку, мойку и страховку берет на себя компания.\r\n\r\n',
                        'price_list_fiat': [300, 500, 1000, 2000, 3000, 5000, 10000],
                        'disclaimer': '<p>Каршеринг BelkaCar — это сервис поминутной аренды автомобилей в Москве. Вы платите только за минуты пользования. За бензин, парковку, мойку и страховку платим мы. Наши авто – KIA Rio, KIA Rio X-Line и Mercedes- Benz CLA\\GLA доступны для аренды в любое время суток. Больше 2125 автомобилей по всему городу в вашем смартфоне! Мобильное приложение доступно для Android и iOS.</p>\r\n<p>Как воспользоваться Сертификатом:</p>\r\n<p>1. Зарегистрируйтесь в сервисе BelkaCar через мобильное приложение или на сайте <a target="_blank" href="https://belkacar.ru/">belkacar.ru</a></p>\r\n<p>2. Загрузите необходимые документы и данные. Дождитесь подтверждения регистрации по СМС или e-mail.</p><p>3. Войдите в приложение BelkaCar</p>\r\n<p>4. До совершения бронирования введите промокод в разделе “Промокод”</p>\r\n<p>5. Можете бронировать автомобиль<br>Воспользоваться сервисом BelkaCar может любой, кому исполнился 21 год и водительский стаж более 2-х лет. Для подключения к сервису BelkaBlack (Mercedes-Benz CLA/GLA) вам должно быть не меньше 25 лет и водительский стаж более 5-ти лет. Перед использованием сервиса настоятельно рекомендуем ознакомится с разделом «Часто задаваемые вопросы», который находится на сайте <a target="_blank" href="https://belkacar.ru/">belkacar.ru</a>.<br>Бронирование автомобиля возможно через приложение и сайт BelkaCar. Аренду можно начать только с помощью приложения. Мобильное приложение доступно для Android и iOS.</p>\r\n<p>Телефон поддержки: +7 (495) 234 33-00</p>',
                        'currency': 'RUB',
                        'coin_price': 1.68,
                        'coin': 'BIP'
                    },
                ]
            },
            'tech': {
                'Cyber-touch.ru': [
                    {
                        'slug': 'giftery-14107',
                        'brief': '...',
                        'price_fiat_min': 100,
                        'price_fiat_max': 100000,
                        'price_fiat_step': 100,
                        'currency': 'RUB',
                        'coin_price': 1.68,
                        'coin': 'BIP'
                    }
                ]
            }

        },
        'test': {'slug': 'gift-t1', 'price_bip': 1, 'coin': 'BIP', 'coin_price': 1.68}
    }
