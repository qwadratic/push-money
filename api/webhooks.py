from flask import Blueprint, request

from api.models import EmailEvent
from providers.gift import gift_webhook_controller

bp_webhooks = Blueprint('webhook', __name__, url_prefix='/webhooks')


@bp_webhooks.route('/gift/<order_id>', methods=['POST'])
def gift_order_result(order_id):
    gift_webhook_controller(request, order_id)
    return ''


@bp_webhooks.route('/sendpulse-mail', methods=['POST'])
def sendpulse_mail_event():
    events = request.get_json()
    EmailEvent.insert_many([{
        'timestamp': int(event['timestamp']),
        'campaign_id': int(event.get('task_id')),
        'addressbook_id': int(event.get('book_id')),
        'event': event.get('event'),
        'email': event.get('email'),
        'event_data': {
            k: event.get(k) for k in [
                'source', 'variables',
                'open_device', 'open_platform',
                'browser_ver', 'browser_name',
                'link_url', 'link_id',
                'from_all', 'reason', 'categories',
                'status', 'status_explain',
            ]}
    } for event in events]).execute()
