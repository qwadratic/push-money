import logging
from time import sleep

import requests
from shortuuid import uuid

from api.models import WebhookEvent
from providers.minter import send_coins

GIFT_WEBHOOK_URL = 'https://push.money/webhooks/gift/{}'
GIFT_API_BASE_URL = 'http://minterfood.ru/miniapi/create_pay.php'


def gift_product_list():
    return {
        'food': {
            'Яндекс.Еда': [
                {'option': 'gift-y1000', 'value': 1000, 'currency': 'RUB'},
                {'option': 'gift-y2000', 'value': 2000, 'currency': 'RUB'},
                {'option': 'gift-y3000', 'value': 3000, 'currency': 'RUB'}
            ]
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
    max_tries = 10
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
    result = send_coins(wallet, to=response['address'], amount=price_bip, wait=True)
    if isinstance(result, str):
        return result

    return gift_order_confirm(response['order_id'])


def gift_webhook_controller(request, order_id):
    logging.info(request.form)
    code = request.form['code']
    WebhookEvent.create(provider='gift', event_id=order_id, event_data={'code': code})
