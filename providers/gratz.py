import logging

import requests

from config import GRATZ_API_KEY
from providers.minter import send_coins

GRATZ_API_BASE_URL = 'https://gratz-bot.click.in.ua/api'
GRATZ_HACK_HEADERS = {'user-agent': 'hack'}  # HTTP 424 if use python std headers :)

CATEGORY_ID_MAPPING = {
    '11': 'tickets',
    '13': 'grocery',
    '14': 'books',
    '15': 'clothing',
    '16': 'kids',
    '18': 'cosmetics',
    '21': 'tech',
    '27': 'gas'
}


def gratz_product_list():
    r = requests.post(
        f'{GRATZ_API_BASE_URL}/list.php',
        data={'key': GRATZ_API_KEY}, headers=GRATZ_HACK_HEADERS)
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        return f"Gratz Provider Error: {data['error']}"

    shops = {d['id']: d for d in data['shops']}
    product_tree = {}
    test_product = None
    for product in data['certificates']:
        product_id = product['id']
        value = int(product['value'])
        if value == 1:
            test_product = {
                'option': f'gratz-{product_id}',
                'value': value,
                'currency': 'BIP'
            }
            continue

        shop_id = product['shop_id']
        shop_name = shops[shop_id]['name']
        category_id = shops[shop_id]['category_id']
        category_name = CATEGORY_ID_MAPPING[category_id]
        product_tree.setdefault(category_name, {})
        product_tree[category_name].setdefault(shop_name, [])
        product_tree[category_name][shop_name].append({
            'option': f'gratz-{product_id}',
            'value': value,
            'currency': 'UAH'
        })
    return product_tree, test_product


def gratz_order_create(product_id):
    r = requests.post(
        f'{GRATZ_API_BASE_URL}/buy.php',
        data={'key': GRATZ_API_KEY, 'id': product_id}, headers=GRATZ_HACK_HEADERS)
    r.raise_for_status()
    data = r.json()
    if 'error' in data:
        return f"Gratz Provider Error: {data['error']}"
    return {
        'price_bip': data['price'],
        'address': data['address'],
        'order_id': data['order_id']
    }


def gratz_order_confirm(address, order_id):
    r = requests.post(
        f'{GRATZ_API_BASE_URL}/check.php',
        data={'key': GRATZ_API_KEY, 'id': order_id, 'address': address}, headers=GRATZ_HACK_HEADERS)
    r.raise_for_status()
    data = r.json()
    return data


def gratz_buy(wallet, product, confirm=True):
    logging.info(f'Buy gratz product id {product}')
    response = gratz_order_create(product)
    if isinstance(response, str):
        return response
    logging.info(f'  order create response {response}')

    price_bip = response['price_bip']
    if not confirm:
        return {'price_bip': price_bip}
    result = send_coins(wallet, to=response['address'], amount=price_bip, wait=True)
    if isinstance(result, str):
        return result

    result = gratz_order_confirm(response['order_id'])
    logging.info(f'  order confirmation response {result}')

    if not result.get('success'):
        return f"Gratz Provider Error: {result['error']}"
    return result
