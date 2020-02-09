import logging
from time import sleep

import requests
from shortuuid import uuid

from api.models import WebhookEvent, OrderHistory
from minter.utils import to_pip
from providers.minter import send_coins

GIFT_WEBHOOK_URL = 'https://push.money/webhooks/gift/{}'
GIFT_API_BASE_URL = 'http://minterfood.ru/miniapi/create_pay.php'


def gift_product_list():
    good = []
    ya_food = ['y1000', 'y2000', 'y3000']
    for product in ya_food:
        response = gift_order_create(product)
        if isinstance(response, dict):
            good.append(product)
        else:
            print(response)
    return {
        'food': {
            'Яндекс.Еда': [
                {
                    'option': f'gift-{p}',
                    'value': int(p[1:]),
                    'currency': 'RUB',
                    'available': p in good
                } for p in ya_food]
        }
    }, {'option': 'gift-t1', 'value': 1, 'currency': 'BIP'}


def gift_order_create(product):
    order_id = uuid()
    payload = {
        'product': product,
        'webhook': GIFT_WEBHOOK_URL.format(order_id)
    }
    r = requests.post(GIFT_API_BASE_URL, data=payload)
    r.raise_for_status()
    data = r.json()
    if not data.get('address'):
        err_msg = data.get('error', data)
        return f'Gift Error: {err_msg}'
    return {
        'price_bip': data['summ'],
        'address': data['address'],
        'order_id': order_id
    }


def gift_order_confirm(order_id):
    max_tries = 20
    tries = 0
    while tries <= max_tries:
        sleep(0.2)
        event = WebhookEvent.get_or_none(event_id=order_id)
        if not event:
            tries += 1
            continue
        code = event.event_data['code']
        event.delete()
        return {'code': code}
    return 'Gift Provider Error: No payment confirmation'


def gift_buy(wallet, product, confirm=True):
    response = gift_order_create(product)
    if isinstance(response, str):
        return response
    price_bip = response['price_bip']

    if not confirm:
        return {'price_bip': price_bip}

    OrderHistory.create(
        provider='gift',
        product_id=product,
        price_pip=str(to_pip(price_bip)),
        address_from=wallet.address,
        address_to=response['address'])

    result = send_coins(wallet, to=response['address'], amount=price_bip, wait=True)
    if isinstance(result, str):
        return result

    return gift_order_confirm(response['order_id'])


def gift_webhook_controller(request, order_id):
    logging.info(request.form)
    code = request.form['code']
    WebhookEvent.create(provider='gift', event_id=order_id, event_data={'code': code})
