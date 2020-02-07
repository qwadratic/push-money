import json
from time import sleep

from pysendpulse.pysendpulse import PySendPulse

from config import SENDPULSE_API_ID, SENDPULSE_API_SECRET

TOKEN_STORAGE = 'memcached'
MAX_CAMPAIGN_SIZE = 10


class CustomSendPulseAPI(PySendPulse):
    def add_campaign(
            self, from_email, from_name, subject, body_or_tmpl_id, addressbook_id, campaign_name='', attachments=None):
        if isinstance(body_or_tmpl_id, str):
            return super().add_campaign(
                from_email, from_name, subject, body_or_tmpl_id, addressbook_id, campaign_name='', attachments=None)
        template_id = body_or_tmpl_id
        if not from_name or not from_email:
            return self._PySendPulse__handle_error('Seems you pass not all data for sender: Email or Name')
        elif not subject or not template_id:
            return self._PySendPulse__handle_error('Seems you pass not all data for task: Title or Template ID')
        elif not addressbook_id:
            return self._PySendPulse__handle_error('Seems you not pass addressbook ID')
        if not attachments:
            attachments = {}
        return self._PySendPulse__handle_result(self._PySendPulse__send_request('campaigns', 'POST', {
            'sender_name': from_name,
            'sender_email': from_email,
            'subject': subject,
            'template_id': template_id,
            'list_id': addressbook_id,
            'name': campaign_name,
            'attachments': json.dumps(attachments)
        }))


SendpulseAPI = CustomSendPulseAPI(SENDPULSE_API_ID, SENDPULSE_API_SECRET, TOKEN_STORAGE)


def prepare_campaign(name, recipients):
    result = SendpulseAPI.add_addressbook(name)
    book_id = result['id']

    SendpulseAPI.add_emails_to_addressbook(book_id, [{
        'email': email,
        'variables': data
    } for email, data in recipients.items()])
    sleep(1)

    result = SendpulseAPI.get_campaign_cost(book_id)
    result = result.get('data', result)
    if result.get('is_error'):
        if result.get('error_code') != 211:
            return
        sleep(1)
        result = SendpulseAPI.get_campaign_cost(book_id)

    to_send = result['sent_emails_qty']
    return {
        'addressbook_id': book_id,
        'to_send': to_send
    }


def campaign_create(book_id):
    result = SendpulseAPI.add_campaign(
        'noreply@push.money', 'YYY Team', '{{name}}, your BIPs are waiting', 194338, book_id)
    return result['id']


def get_campaign_stats(campaign_id):
    response = SendpulseAPI.get_campaign_info(campaign_id)

    if not campaign_id or response.get('data', {}).get('is_error'):
        return {
            'n_emails': 0,
            'send_date': None,
            'finished': False,
            'sent': 0,
            'delivered': 0,
            'opened': 0,
            'clicked': 0
        }
    stats = response['statistics']
    stat_codes = {
        1: 'sent',
        2: 'delivered',
        3: 'opened',
        4: 'clicked'
    }
    stats = {
        stat_codes.get(stat['code']): stat['count']
        for stat in stats if stat_codes.get(stat['code'])
    }
    stats['n_emails'] = response['all_email_qty']
    stats['send_date'] = response['send_date']
    stats['finished'] = response['status'] in [3, 5, 25, 27]
    return stats
