from time import sleep

from pysendpulse.pysendpulse import PySendPulse

from config import SENDPULSE_API_ID, SENDPULSE_API_SECRET

TOKEN_STORAGE = 'memcached'

SendpulseAPI = PySendPulse(SENDPULSE_API_ID, SENDPULSE_API_SECRET, TOKEN_STORAGE)

MAX_CAMPAIGN_SIZE = 10


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
