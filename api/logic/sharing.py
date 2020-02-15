from gspread import Spreadsheet
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import fn

from api.logic.core import generate_and_save_wallet
from api.models import PushCampaign, Recipient, PushWallet
from minter.utils import to_pip, to_bip
from providers.google_sheets import get_spreadsheet, parse_recipients
from providers.minter import ensure_balance


def get_google_sheet_data(sheet_url):
    spreadsheet_or_error = get_spreadsheet(sheet_url)
    if isinstance(spreadsheet_or_error, dict):
        return spreadsheet_or_error
    if not isinstance(spreadsheet_or_error, Spreadsheet):
        return 'Internal API error'
    recipients = parse_recipients(spreadsheet_or_error)

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.02 * len(recipients)
    campaign_cost = total_cost + total_fee
    return recipients, campaign_cost


def create_campaign(
        recipients, sender, cost,
        campaign_pass=None, wallet_pass=None, target=None, customization_id=None):
    campaign_pass_hash = pbkdf2_sha256.hash(campaign_pass) if campaign_pass is not None else None
    campaign_wallet = generate_and_save_wallet()
    campaign = PushCampaign.create(
        wallet_link_id=campaign_wallet.link_id,
        status='open',
        cost_pip=str(to_pip(cost)),
        company=sender,
        password_hash=campaign_pass_hash)

    for info in recipients.values():
        balance = str(to_pip(info['amount'] + 0.01))
        wallet = generate_and_save_wallet(
            sender=sender, recipient=info['name'], password=wallet_pass,
            campaign_id=campaign.id, virtual_balance=balance,
            customization_setting_id=customization_id)
        info['token'] = wallet.link_id

    Recipient.bulk_create([Recipient(
        email=email, campaign_id=campaign.id,
        name=info['name'], amount_pip=str(to_pip(info['amount'])),
        wallet_link_id=info['token'], target_shop=target,
        customization_setting_id=customization_id
    ) for email, info in recipients.items()], batch_size=100)
    return campaign, campaign_wallet


def check_campaign_paid(campaign):
    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    is_paid = ensure_balance(wallet.address, campaign.cost_pip)
    if is_paid:
        campaign.status = 'paid'
        campaign.save()
    return is_paid


def get_campaign_stats(campaign, extended=False):
    if extended:
        sent_list = campaign.recipients \
            .select().where(Recipient.sent_at.is_null(False)) \
            .order_by(Recipient.sent_at.asc())
        return {
            'customization_id': campaign.customization_setting_id,
            'status': campaign.status,
            'recipients': [{
                'email': r.email, 'name': r.name,
                'amount_bip': float(to_bip(r.amount_pip)),
                'sent_at': r.sent_at,
                'opened_at': r.opened_at,
                'clicked_at': r.linked_at,
                'push_id': r.wallet_link_id,
                'target': r.target_shop
            } for r in sent_list]
        }
    result = campaign.recipients.select(
        fn.COUNT(Recipient.created_at).alias('emails'),
        fn.COUNT(Recipient.sent_at).alias('sent'),
        fn.COUNT(Recipient.opened_at).alias('open'),
        fn.COUNT(Recipient.linked_at).alias('clicked'))
    summary = result[0] if result else None
    result = {
        'customization_id': campaign.customization_setting_id,
        'status': campaign.status,
        'sent': 0,
        'open': 0,
        'clicked': 0
    }
    if not summary:
        return result
    return {
        'customization_id': campaign.customization_setting_id,
        'sent': summary.sent,
        'open': summary.open,
        'clicked': summary.clicked,
        'status': campaign.status
    }
