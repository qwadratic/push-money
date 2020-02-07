from time import sleep

import requests
from shortuuid import uuid

from api.models import WebhookEvent
from providers.minter import send_coins

GIFT_WEBHOOK_URL = 'https://push.money/webhooks/gift/{}'
GIFT_API_BASE_URL = 'http://minterfood.ru/miniapi/create_pay.php'


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
        return 'Product not found'
    return {'price_bip': data['summ'], 'address': data['address'], 'order_id': order_id}


def gift_webhook_controller(request, order_id):
    print(request.get_json())
    code = request.get_json()['code']
    WebhookEvent.create(provider='gift', event_id=order_id, event_data={'code': code})


def gift_buy(wallet, product):
    response = gift_order_create(product)
    if isinstance(response, str):
        return response

    send_coins(wallet, to=response['address'], amount=response['price_bip'], wait=True)

    while True:
        sleep(0.2)
        event = WebhookEvent.get_or_none(event_id=response['order_id'])
        if not event:
            continue
        code = event.event_data['code']
        event.delete()
        return {'code': code}
