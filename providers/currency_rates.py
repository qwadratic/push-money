from typing import Dict

import requests
from cachetools.func import ttl_cache

from helpers.misc import retry


ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE

MINTER1001_BASE_URL = 'https://minter.1001btc.com/en'
RATES_API_BASE_URL = 'https://api.exchangeratesapi.io'
PRIVAT24_API_BASE_URL = 'https://api.privatbank.ua/p24api'


@ttl_cache(ttl=10 * ONE_MINUTE)
@retry(requests.HTTPError, tries=3, delay=3, backoff=2)
def get_cfg():
    r = requests.get(f'{MINTER1001_BASE_URL}/getcfg')
    r.raise_for_status()
    return r.json()


@ttl_cache(ttl=ONE_HOUR)
@retry(requests.HTTPError, tries=3, delay=3, backoff=2)
def ecb_usd_rates():
    """European Central Bank rates"""
    r = requests.get(f'{RATES_API_BASE_URL}/latest', params={'base': 'USD'})
    r.raise_for_status()
    return r.json()['rates']


@ttl_cache(ttl=ONE_HOUR)
@retry(requests.HTTPError, tries=3, delay=3, backoff=2)
def privat24_usd_uah():
    params = {
        'coursid': 5,
        'json': True,
        'exchange': True
    }
    r = requests.get(f'{PRIVAT24_API_BASE_URL}/pubinfo', params=params)
    r.raise_for_status()
    rates_list = r.json()
    buy_rates = {rate['ccy']: float(rate['buy']) for rate in rates_list}
    return buy_rates.get('USD', 30)


def bip_to_usdt(bip_value) -> float:
    if bip_value == 0:
        return 0

    cfg = get_cfg()

    usdt_rate = float(cfg['bip2usdt'])
    # usdt_fee = float(cfg['usdt_comission'])
    # min_no_fee = float(cfg['bip2usdt_min_sum4nofee'])

    # fee = usdt_fee if bip_value < min_no_fee else 0
    usdt = float(bip_value) * usdt_rate
    return usdt


def fiat_to_usd_rates() -> Dict[str, float]:
    ecb_rates = ecb_usd_rates()
    uah_usd = privat24_usd_uah()
    return {'UAH': uah_usd, **ecb_rates}


def bip_price() -> float:
    ecb_rates = ecb_usd_rates()
    usd2rub = ecb_rates['RUB']

    cfg = get_cfg()
    usdt2bip = float(cfg['usdt2bip'])

    return round(usdt2bip * usd2rub, 2)


def rub_to_bip(value) -> float:
    if not value:
        return 0

    value = float(value)

    ecb_rates = ecb_usd_rates()
    rub2usd_rate = ecb_rates['RUB']

    cfg = get_cfg()
    bip2usdt_rate = float(cfg['bip2usdt'])

    return float(value / rub2usd_rate) / bip2usdt_rate
