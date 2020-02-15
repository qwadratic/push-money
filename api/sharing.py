import decimal
from decimal import Decimal

from flask import Blueprint, request, jsonify

from api.consts import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND, HTTP_401_UNAUTHORIZED
from api.logic.sharing import get_google_sheet_data, create_campaign, check_campaign_paid, get_campaign_stats
from api.models import PushCampaign, PushWallet
from minter.helpers import create_deeplink
from providers.minter import get_balance, send_coins, get_first_transaction

bp_sharing = Blueprint('sharing', __name__, url_prefix='/api/sharing')


@bp_sharing.route('/validate-source', methods=['POST'])
def validate_google_sheet():
    """
    swagger: swagger/sharing/validate-source.yml
    """
    payload = request.get_json() or {}
    spreadsheet_url = payload.get('source')
    if not spreadsheet_url:
        return jsonify({'error': 'Sheet url not specified'}), HTTP_400_BAD_REQUEST

    result = get_google_sheet_data(spreadsheet_url)
    if isinstance(result, dict):
        return jsonify(result), HTTP_400_BAD_REQUEST
    if isinstance(result, str):
        return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients, campaign_cost = result
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    return jsonify({
        'total_bip': campaign_cost,
        'total_emails': len(recipients)
    })


@bp_sharing.route('/create', methods=['POST'])
def campaign_create():
    """
    swagger: swagger/sharing/campaign-create.yml
    """
    payload = request.get_json() or {}
    sender = payload.get('sender') or None
    spreadsheet_url = payload.get('source')
    target = payload.get('target') or None
    wall_pass = payload.get('wallet_pass') or None
    cmp_pass = payload.get('campaign_pass') or None
    customization_setting_id = payload.get('customization_setting_id') or None

    if not spreadsheet_url:
        return jsonify({'error': 'Sheet url not specified'}), HTTP_400_BAD_REQUEST

    result = get_google_sheet_data(spreadsheet_url)
    if isinstance(result, dict):
        return jsonify(result), HTTP_400_BAD_REQUEST
    if isinstance(result, str):
        return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients, campaign_cost = result
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    campaign, campaign_wallet = create_campaign(
        recipients, sender, campaign_cost,
        campaign_pass=cmp_pass,
        wallet_pass=wall_pass,
        target=target,
        customization_id=customization_setting_id)

    return jsonify({
        'campaign_id': campaign.id,
        'address': campaign_wallet.address,
        'deeplink': create_deeplink(campaign_wallet.address, campaign_cost),
        'total_bip': campaign_cost
    })


@bp_sharing.route('/<int:campaign_id>/check-payment')
def campaign_check(campaign_id):
    """
    swagger: swagger/sharing/campaign-check.yml
    """
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    is_paid = check_campaign_paid(campaign)
    return jsonify({'result': is_paid})


@bp_sharing.route('/<int:campaign_id>/stats', methods=['GET', 'POST'])
def campaign_stats(campaign_id):
    """
    swagger: swagger/sharing/campaign-stats.yml
    """
    payload = request.get_json() or {}
    password = payload.get('password')
    extended = bool(int(request.args.get('extended', "0")))

    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    if not campaign.auth(password):
        return jsonify({'error': 'Incorrect password'}), HTTP_401_UNAUTHORIZED

    stats = get_campaign_stats(campaign, extended=extended)
    return jsonify(stats)


@bp_sharing.route('/<int:campaign_id>/close', methods=['POST'])
def campaign_close(campaign_id):
    """
    swagger: swagger/sharing/campaign-close.yml
    """
    payload = request.get_json() or {}
    password = payload.get('password')
    confirm = bool(int(request.args.get('confirm', "0")))

    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND
    if not campaign.auth(password):
        return jsonify({'error': 'Incorrect password'}), HTTP_401_UNAUTHORIZED

    decimal.getcontext().rounding = decimal.ROUND_DOWN
    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    amount_left = round(Decimal(get_balance(wallet.address, bip=True) - 0.01), 4)
    return_address = get_first_transaction(wallet.address)

    if confirm:
        campaign.status = 'closed'
        campaign.save()
        if amount_left > 0:
            result = send_coins(wallet, return_address, amount_left, wait=True)
            # тут скорее всего есть баг - нужно еще виртуальные балансы обнулять
            # иначе с рассылки придет челик, проверит баланс, увидит виртуальный
            # и продукт встретит его пятисоткой потому что на балансе кампании 0
            if result is not True:
                return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    return jsonify({
        'amount_left': float(amount_left) if amount_left >= 0 else 0,
        'return_address': return_address
    })
