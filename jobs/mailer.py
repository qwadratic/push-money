import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from api.models import PushCampaign, PushWallet, OrderHistory, CustomizationSetting, UserImage
from api.upload import images
from config import EMAIL_PASS, SMTP_HOST, EMAIL_SENDER, GRATZ_OWNER_EMAIL, DEV_EMAIL, SMTP_PORT
from jobs.scheduler import scheduler
from mintersdk.shortcuts import to_bip

SHARING_MSG_TMPL = open('content/mail-pixel.html').read()
SHARING_TMPL_DEFAULT_VARS = {
    'email_image_url': 'https://s7316426.sendpul.se/files/emailservice/userfiles/bd1aa7bbad3801dda999d8e93d0b4c287316426/Frame_6_email_1.png',
    'email_head_text': '{name}, Вы получили подарок от {company} — {amount} BIP!',
    'email_body_text': 'Нажмите на кнопку, чтобы потратить их или вывести на свой Minter-кошелек.',
    'email_button_text': 'Открыть кошелек',
    'email_subject_text': '[YYY] Привет, {name}! Тебе подарок от {company}'
}

GRATZ_NOTIFICATION_TMPL = """\
Subject: [YYY important] New order

New order received: {product_name}
Contact: {contact}
API response: {api_response}
"""


def build_custom_email(person, campaign):
    name, company, amount, recipient_id = \
        person.name, campaign.company, str(to_bip(person.amount_pip)), str(person.id)
    customization = CustomizationSetting.get_or_none(id=campaign.customization_setting_id)

    msg_variables_tmpl = SHARING_TMPL_DEFAULT_VARS.copy()
    if customization:
        img = UserImage.get_or_none(id=customization.email_image_id)
        with scheduler.app.app_context():
            custom_img_url = images.url(img.filename) if img else None
        changes = {
            'email_image_url': custom_img_url,
            'email_head_text': customization.email_head_text,
            'email_body_text': customization.email_body_text,
            'email_button_text': customization.email_button_text,
            'email_subject_text': customization.email_subject_text,
        }
        msg_variables_tmpl.update(**{k: v for k, v in changes.items() if v is not None})
    msg_variables = {
        k: v.format(name=name, company=company, amount=amount)
        for k, v in msg_variables_tmpl.items()
    }

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = person.email
    msg['Subject'] = msg_variables['email_subject_text']
    html_body = SHARING_MSG_TMPL \
        .replace('{{email_image_url}}', msg_variables['email_image_url']) \
        .replace('{{email_head_text}}', msg_variables['email_head_text']) \
        .replace('{{email_body_text}}', msg_variables['email_body_text']) \
        .replace('{{email_button_text}}', msg_variables['email_button_text']) \
        .replace('{{token}}', person.wallet_link_id + person.target_route) \
        .replace('{{recipient_id}}', recipient_id)
    msg.attach(MIMEText(html_body, 'html'))
    return msg


def send_mail(campaign):
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASS)

        for person in campaign.recipients:
            msg = build_custom_email(person, campaign)
            server.send_message(msg)
            person.sent_at = datetime.utcnow()
            person.save()
            logging.info(f'[Campaign {campaign.company}] sent email to {person.email}')

        campaign.status = 'completed'
        campaign.save()


@scheduler.scheduled_job('interval', seconds=30, disable_dev=True)
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

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASS)
        for email in [GRATZ_OWNER_EMAIL, DEV_EMAIL]:
            server.sendmail(EMAIL_SENDER, email, message)
        order.notified = True
        order.save()


def schedule_gratz_notification(order_id, api_response, product_name):
    scheduler.add_job(send_gratz_notification, 'date', args=(order_id, api_response, product_name))
