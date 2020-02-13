import decimal
from decimal import Decimal

from flask import Blueprint, request, jsonify
from gspread import Spreadsheet
from peewee import fn

from api.consts import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_404_NOT_FOUND
from api.logic.core import generate_and_save_wallet
from api.models import PushCampaign, PushWallet, Recipient
from minter.helpers import create_deeplink
from minter.utils import to_pip, to_bip
from providers.google_sheets import get_spreadsheet, parse_recipients
from providers.minter import ensure_balance, get_balance, send_coins, get_first_transaction

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

    spreadsheet_or_error = get_spreadsheet(spreadsheet_url)

    if isinstance(spreadsheet_or_error, dict):
        return jsonify(spreadsheet_or_error), HTTP_400_BAD_REQUEST
    elif not isinstance(spreadsheet_or_error, Spreadsheet):
        return jsonify({'error': 'Internal API error'}), HTTP_500_INTERNAL_SERVER_ERROR

    recipients = parse_recipients(spreadsheet_or_error)
    if not recipients:
        return jsonify({'error': 'Recipient list is empty'}), HTTP_400_BAD_REQUEST

    total_cost = sum(info['amount'] for info in recipients.values())
    total_fee = 0.02 * len(recipients)
    return jsonify({
        'total_bip': total_cost + total_fee,
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
    wallet_pass = payload.get('wallet_pass') or None
    campaign_pass = payload.get('campaign_pass') or None

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
    total_fee = 0.02 * len(recipients)
    campaign_cost = total_cost + total_fee

    campaign_wallet = generate_and_save_wallet()
    campaign = PushCampaign.create(
        wallet_link_id=campaign_wallet.link_id,
        status='open',
        cost_pip=str(to_pip(campaign_cost)),
        company=sender,
        password=campaign_pass)

    for info in recipients.values():
        balance = str(to_pip(info['amount'] + 0.01))
        wallet = generate_and_save_wallet(
            sender=sender, recipient=info['name'], password=wallet_pass,
            campaign_id=campaign.id, virtual_balance=balance)
        info['token'] = wallet.link_id

    Recipient.bulk_create([Recipient(
        email=email, campaign_id=campaign.id,
        name=info['name'], amount_pip=str(to_pip(info['amount'])),
        wallet_link_id=info['token'], target=target
    ) for email, info in recipients.items()])

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
    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    if not ensure_balance(wallet.address, campaign.cost_pip):
        return jsonify({'result': False})
    campaign.status = 'paid'
    campaign.save()
    return jsonify({'result': True})


@bp_sharing.route('/<int:campaign_id>/stats', methods=['GET'])
def campaign_stats(campaign_id):
    """
    swagger: swagger/sharing/campaign-stats
    """
    campaign = PushCampaign.get_or_none(id=campaign_id)
    password = request.args.get('password')
    if not campaign or (campaign.password is not None and campaign.password != password):
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND

    extended = bool(int(request.args.get('extended', "0")))
    if extended:
        sent_list = campaign.recipients \
            .select().where(Recipient.sent_at.is_null(False)) \
            .order_by(Recipient.sent_at.asc())
        return jsonify({
            'status': campaign.status,
            'recipients': [{
                'email': r.email, 'name': r.name,
                'amount_bip': float(to_bip(r.amount_pip)),
                'sent_at': r.sent_at,
                'opened_at': r.opened_at,
                'clicked_at': r.linked_at,
                'push_id': r.wallet_link_id,
                'target': r.target
            } for r in sent_list]
        })

    stat = campaign.recipients.select(
        fn.COUNT(Recipient.created_at).alias('emails'),
        fn.COUNT(Recipient.sent_at).alias('sent'),
        fn.COUNT(Recipient.opened_at).alias('open'),
        fn.COUNT(Recipient.linked_at).alias('clicked'))
    if stat:
        stat = stat[0]
    return jsonify({
        'sent': stat.sent,
        'open': stat.open,
        'clicked': stat.clicked,
        'status': campaign.status
    })


@bp_sharing.route('/<int:campaign_id>/close', methods=['POST'])
def campaign_close(campaign_id):
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    campaign = PushCampaign.get_or_none(id=campaign_id)
    if not campaign:
        return jsonify({'error': 'Campaign not found'}), HTTP_404_NOT_FOUND

    # временно
    # if campaign.status != 'completed':
    #     return jsonify({
    #         'error': f"Can stop only 'completed' campaign. Current status: {campaign.status}"}), HTTP_400_BAD_REQUEST

    confirm = bool(int(request.args.get('confirm', "0")))

    wallet = PushWallet.get(link_id=campaign.wallet_link_id)
    amount_left = round(Decimal(get_balance(wallet.address, bip=True) - 0.01), 4)
    return_address = get_first_transaction(wallet.address)

    if confirm:
        campaign.status = 'closed'
        campaign.save()
        if amount_left > 0:
            result = send_coins(wallet, return_address, amount_left, wait=True)
            # тут скорее всего есть баг - нужно еще виртуальные балансы обнулять
            # иначе с рассылки придет челик, проверит баланс, применит виртуальный
            # и продукт встретит его пятисоткой потому что на балансе кампании 0
            if result is not True:
                return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    return jsonify({
        'amount_left': float(amount_left) if amount_left >= 0 else 0,
        'return_address': return_address
    })
