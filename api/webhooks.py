from flask import Blueprint, request

from providers.gift import gift_webhook_controller

bp_webhooks = Blueprint('webhook', __name__, url_prefix='/webhooks')


@bp_webhooks.route('/gift/<order_id>', methods=['POST'])
def gift_order_result(order_id):
    gift_webhook_controller(request, order_id)
    return ''