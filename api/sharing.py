from flask import Blueprint, request, jsonify
from gspread import Spreadsheet

from api.consts import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND
from api.logic.core import generate_and_save_wallet
from api.models import PushCampaign, PushWallet, Recipient
from minter.helpers import create_deeplink
from minter.utils import to_pip
from providers.google_sheets import get_spreadsheet, parse_recipients
from providers.minter import ensure_balance, get_balance, send_coins, get_first_transaction

bp_sharing = Blueprint('sharing', __name__, url_prefix='/api/sharing')


@bp_sharing.route('/validate-source', methods=['POST'])
def validate_google_sheet():
    payload = request.get_json() or {}
    spreadsheet_url = payload.get('source')
    if not spreadsheet_url:
        return jsonify({'error': 'Sheet url not specified'}), HTTP_400_BAD_REQUEST

    spreadsheet_or_error = get_spreadsheet(spreadsheet_url)

    if isinstance(spreadsheet_or_error, dict):
        return jsonify(spreadsheet_or_error), HTTP_400_BAD_REQUEST
    elif not isinstance(spreadsheet_or_error, Spreadsheet):
        return jsonify({'error': 'Internal API error'}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients = parse_recipients(spreadsheet_or_error)
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.01 * len(recipients)
    return jsonify({
        'total_bip': total_cost + total_fee,
        'total_emails': len(recipients)
    })


@bp_sharing.route('/create', methods=['POST'])
def campaign_create():
    payload = request.get_json() or {}
    sender = payload.get('sender') or None
    spreadsheet_url = payload.get('source')
    target = payload.get('target') or None
    password = payload.get('password') or None

    if not spreadsheet_url:
        return jsonify({'error': 'Sheet url not specified'}), HTTP_400_BAD_REQUEST

    spreadsheet_or_error = get_spreadsheet(spreadsheet_url)

    if isinstance(spreadsheet_or_error, dict):
        return jsonify(spreadsheet_or_error), HTTP_400_BAD_REQUEST
    elif not isinstance(spreadsheet_or_error, Spreadsheet):
        return jsonify({'error': 'Internal API error'}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients = parse_recipients(spreadsheet_or_error)
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.01 * len(recipients)
    campaign_cost = total_cost + total_fee

    campaign_wallet = generate_and_save_wallet()
    campaign = PushCampaign.create(
        wallet_link_id=campaign_wallet.link_id,
        status='open',
        cost_pip=str(to_pip(campaign_cost)),
        company=sender)

    for info in recipients.values():
        balance = str(to_pip(info['amount']))
        wallet = generate_and_save_wallet(
            sender=sender, recipient=info['name'], password=password,
            campaign_id=campaign.id, virtual_balance=balance,
            target=target)
        info['token'] = wallet.link_id

    Recipient.bulk_create([Recipient(
        email=email, campaign_id=campaign.id,
        name=info['name'], amount_pip=str(to_pip(info['amount'])),
        wallet_link_id=info['token']
    ) for email, info in recipients.items()])

    return jsonify({
        'campaign_id': campaign.id,
        'address': campaign_wallet.address,
        'deeplink': create_deeplink(campaign_wallet.address, campaign_cost),
        'total_bip': campaign_cost
    })


@bp_sharing.route('/<int:campaign_id>/check-payment')
def campaign_check(campaign_id):
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    if not ensure_balance(wallet.address, campaign.cost_pip):
        return jsonify({'result': False})
    campaign.status = 'paid'
    campaign.save()
    return jsonify({'result': True})


@bp_sharing.route('/<int:campaign_id>/stats')
def campaign_stats(campaign_id):
    return {
        'n_emails': 0,
        'send_date': None,
        'finished': False,
        'sent': 0,
        'delivered': 0,
        'opened': 0,
        'clicked': 0
    }
    # campaign = PushCampaign.get_or_none(id=campaign_id)
    # if not campaign:
    #     return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    # stats = get_campaign_stats(campaign.sendpulse_campaign_id)
    # if stats['finished']:
    #     campaign.status = 'completed'
    #     campaign.save()

    # EmailEvent.select(EmailEvent) \
    #     .where(
    #         (EmailEvent.campaign_id == campaign.sendpulse_campaign_id |
    #          EmailEvent.addressbook_id == campaign.sendpulse_addressbook_id) &
    #         EmailEvent.event.in_(['spam', 'open', 'redirect'])) \
    #     .order_by(EmailEvent.timestamp.asc())
    # return stats


@bp_sharing.route('/<int:campaign_id>/close', methods=['POST'])
def campaign_close(campaign_id):
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND

    # временно
    # if campaign.status != 'completed':
    #     return jsonify({
    #         'error': f"Can stop only 'completed' campaign. Current status: {campaign.status}"}), HTTP_400_BAD_REQUEST

    confirm = bool(int(request.args.get('confirm', 0)))

    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    amount_left = get_balance(wallet.address, bip=True) - 0.01
    return_address = get_first_transaction(wallet.address)

    if confirm:
        campaign.status = 'closed'
        campaign.save()
        if amount_left > 0:
            result = send_coins(wallet, return_address, amount_left, wait=True)
            if result is not True:
                return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    return jsonify({
        'amount_left': amount_left if amount_left >= 0 else 0,
        'return_address': return_address
    })


# вебхук статистики:
#   - сохраняет детальную статистику по кампаниям
