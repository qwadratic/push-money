import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.models import PushCampaign, PushWallet, OrderHistory
from config import MAIL_PASS
from jobs.scheduler import scheduler
from minter.utils import to_bip

msg_template = open('jobs/mail-pixel.html').read()
subj_template = '[GIFT] Hi, {name}, {company} sent you a gift!'
host = 'smtp-mail.outlook.com'
sender = "noreply@push.money"
GRATZ_OWNER_EMAIL = 'amperluxe@gmail.com'
DEV_EMAIL = 'ivan.d.kotelnikov@gmail.com'
GRATZ_NOTIFICATION_TMPL = """\
Subject: [YYY important] New order

New order received: {product_name}
Contact: {contact}
API response: {api_response}
"""


def _make_message(person, company):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = person.email
    msg['Subject'] = subj_template.format(name=person.name, company=company)
    token = person.wallet_link_id + person.target_route
    message = msg_template \
        .replace('{{name}}', person.name) \
        .replace('{{amount}}', str(to_bip(person.amount_pip))) \
        .replace('{{token}}', token) \
        .replace('{{company}}', company) \
        .replace('{{recipient_id}}', str(person.id))
    msg.attach(MIMEText(message, 'html'))
    return msg


def send_mail(campaign):
    company = campaign.company or 'Unknown Company'

    with smtplib.SMTP(host, 587) as server:
        server.starttls()
        server.login(sender, MAIL_PASS)

        for person in campaign.recipients:
            msg = _make_message(person, company)
            server.send_message(msg)
            person.sent_at = datetime.utcnow()
            person.save()
            logging.info(f'[Campaign {company}] sent email to {person.email}')

        campaign.status = 'completed'
        campaign.save()


@scheduler.scheduled_job('interval', seconds=30)
def job_execute_campaigns():
    to_start = PushCampaign \
        .select(PushCampaign, PushWallet) \
        .join(PushWallet, on=PushCampaign.wallet_link_id == PushWallet.link_id) \
        .where(PushCampaign.status == 'paid')

    for campaign in to_start:
        campaign.status = 'progress'
        campaign.save()
        scheduler.add_job(send_mail, 'date', args=(campaign,))


def send_gratz_notification(order_id, api_response, product_name):
    order = OrderHistory.get_or_none(id=order_id)
    if not order:
        return
    message = GRATZ_NOTIFICATION_TMPL.format(
        product_name=product_name,
        contact=order.contact,
        api_response=api_response)

    with smtplib.SMTP(host, 587) as server:
        server.starttls()
        server.login(sender, MAIL_PASS)
        for email in [GRATZ_OWNER_EMAIL, DEV_EMAIL]:
            server.sendmail(sender, email, message)
        order.notified = True
        order.save()


def schedule_gratz_notification(order_id, api_response, product_name):
    scheduler.add_job(send_gratz_notification, 'date', args=(order_id, api_response, product_name))
