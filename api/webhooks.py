import logging

from flask import Blueprint, request, send_file

from providers.gift import gift_webhook_controller

bp_webhooks = Blueprint('webhook', __name__, url_prefix='/webhooks')


@bp_webhooks.route('/gift/<order_id>', methods=['POST'])
def gift_order_result(order_id):
    gift_webhook_controller(request, order_id)
    return ''


@bp_webhooks.route('/pixel/<mail_stat_id>', methods=['GET'])
def pixel(mail_stat_id):
    logging.info(f"PIXEL WORKS {mail_stat_id}")
    return send_file(open('api/templates/pixel.gif', 'rb'), mimetype='image/gif')
