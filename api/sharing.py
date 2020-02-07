from flask import Blueprint, request, jsonify
from gspread import Spreadsheet

from api.consts import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND
from api.logic.core import generate_and_save_wallet
from api.models import PushCampaign, PushWallet
from minter.helpers import create_deeplink
from minter.utils import to_pip
from providers.google_sheets import get_spreadsheet, parse_recipients
from providers.minter import ensure_balance
from providers.sendpulse import prepare_campaign

bp_sharing = Blueprint('sharing', __name__, url_prefix='/api/sharing')


# https://docs.google.com/spreadsheets/d/16daTxWC-EyTQ0L1LZSoQP09MTu0_LOnzDwOuVJSp5Qo/edit#gid=1668559759

@bp_sharing.route('/email-import', methods=['POST'])
def email_import():
    payload = request.get_json() or {}
    spreadsheet_url = payload.get('google_sheet_url')
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

    campaign_wallet = generate_and_save_wallet(None, None, None)
    campaign = PushCampaign.create(wallet_link_id=campaign_wallet.link_id)

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.01 * len(recipients)
    campaign_cost = total_cost + total_fee

    for info in recipients.values():
        wallet = generate_and_save_wallet(None, None, None)
        info['token'] = wallet.link_id
    campaign_info = prepare_campaign(f'dev_{campaign.wallet_link_id}', recipients)
    campaign.sendpulse_addressbook_id = campaign_info['addressbook_id']
    campaign.cost_pip = str(to_pip(campaign_cost))
    campaign.save()

    return jsonify({
        'campaign_id': campaign.id,
        'address': campaign_wallet.address,
        'deeplink': create_deeplink(campaign_wallet.address, campaign_cost),
        'recipients': [{
            'email': email,
            'name': info['name'],
            'amount': info['amount'],
            'link_id': info['token']
        } for email, info in recipients.items()]
    })


@bp_sharing.route('/<int:campaign_id>/check-payment')
def campaign_check(campaign_id):
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    if not ensure_balance(wallet.address, campaign.cost_pip):
        return jsonify({'result': False})
    return jsonify({'result': True})


@bp_sharing.route('/<int:campaign_id>/stats')
def campaign_stats(campaign_id):
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    stats = campaign_stats(campaign.sendpulse_campaign_id)
    return stats


@bp_sharing.route('/<int:campaign_id>/close', methods=['POST'])
def campaign_close(campaign_id):
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND

    # временно
    if campaign.status != 'completed':
        return jsonify({
            'error': f"Can stop only 'completed' campaign. Current status: {campaign.status}"}), HTTP_400_BAD_REQUEST

    campaign.status = 'closed'
    campaign.save()

    # возврат денег
    amount_left = 0
    return jsonify({'amount_left': amount_left})


# вебхук статистики:
#   - сохраняет детальную статистику по кампаниям
