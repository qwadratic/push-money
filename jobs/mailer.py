import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.models import PushCampaign, PushWallet, Recipient
from jobs.scheduler import scheduler
from minter.utils import to_bip

msg_template = open('jobs/mail-template.html').read()
subj_template = '[GIFT] Hi, {name}, {company} sent you a gift!'
host = 'smtp-mail.outlook.com'
sender = "noreply@push.money"
password = "bychevoz13"


def _make_message(email, name, amount, token, company, recipient_id):
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = email
    msg['Subject'] = subj_template.format(name=name, company=company)
    message = msg_template \
        .replace('{{name}}', name) \
        .replace('{{amount}}', str(amount)) \
        .replace('{{token}}', token) \
        .replace('{{company}}', company) \
        .replace('{{recipient_id}}', recipient_id)
    msg.attach(MIMEText(message, 'html'))
    return msg


def send_mail(campaign):
    company = campaign.company or 'Unknown Company'

    with smtplib.SMTP(host, 587) as server:
        server.starttls()
        server.login(sender, password)

        for person in campaign.recipients:
            msg = _make_message(
                person.email, person.name, to_bip(person.amount_pip),
                person.wallet_link_id, company, person.id)
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
