from flask import Blueprint, jsonify, request, url_for

from api.consts import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from api.logic.core import generate_and_save_wallet, get_address_balance, get_spend_categories, spend_balance
from api.models import PushWallet, PushCampaign
from minter.helpers import create_deeplink
from minter.utils import to_bip
from providers.minter import send_coins

bp_api = Blueprint('api', __name__, url_prefix='/api')


@bp_api.route('/', methods=['GET'])
def health():
    return f'Api ok. <a href={url_for("root.readme")}>Guide</a>'


@bp_api.route('/push/create', methods=['POST'])
def push_create():
    payload = request.get_json() or {}
    sender, recipient = payload.get('sender'), payload.get('recipient')
    password = payload.get('password')
    amount = payload.get('amount')

    wallet = generate_and_save_wallet(
        sender=sender, recipient=recipient, password=password)
    response = {
        'address': wallet.address,
        'link_id': wallet.link_id
    }
    if amount:
        response['deeplink'] = create_deeplink(wallet.address, float(amount) + 0.01)
    return jsonify(response)


@bp_api.route('/push/<link_id>/info', methods=['GET'])
def push_info(link_id):
    wallet = PushWallet.get_or_none(link_id=link_id)
    if not wallet:
        return jsonify({'error': 'Link does not exist'}), HTTP_404_NOT_FOUND

    return jsonify({
        'target': wallet.target,
        'sender': wallet.sender,
        'recipient': wallet.recipient,
        'is_protected': wallet.password_hash is not None
    })


@bp_api.route('/push/<link_id>/balance', methods=['GET', 'POST'])
def push_balance(link_id):
    payload = request.get_json() or {}
    password = payload.get('password')

    wallet = PushWallet.get_or_none(link_id=link_id)
    if not wallet:
        return jsonify({'error': 'Link does not exist'}), HTTP_404_NOT_FOUND

    if not wallet.auth(password):
        return jsonify({'error': 'Incorrect password'}), HTTP_401_UNAUTHORIZED

    # зарефакторить
    virtual_balance = None if wallet.virtual_balance == '0' else wallet.virtual_balance
    if virtual_balance is not None and not wallet.seen:
        cmp = PushCampaign.get(id=wallet.campaign_id)
        cmp_wallet = PushWallet.get(link_id=cmp.wallet_link_id)
        result = send_coins(cmp_wallet, wallet.address, amount=to_bip(wallet.virtual_balance), wait=False)
        if result is not True:
            return jsonify({'error': result}), HTTP_500_INTERNAL_SERVER_ERROR
        wallet.seen = True
        wallet.virtual_balance = '0'
        wallet.save()

    balance = get_address_balance(wallet.address, virtual=virtual_balance)
    response = {
        'address': wallet.address,
        **balance
    }
    return jsonify(response)


@bp_api.route('/spend/list', methods=['GET'])
def spend_options():
    categories = get_spend_categories()
    return jsonify(categories)


@bp_api.route('/spend/<link_id>', methods=['POST'])
def make_spend(link_id):
    payload = request.get_json() or {}
    password = payload.get('password')

    wallet = PushWallet.get_or_none(link_id=link_id)
    if not wallet:
        return jsonify({'success': False, 'error': 'Link does not exist'}), HTTP_404_NOT_FOUND

    if 'option' not in payload:
        return jsonify({'success': False, 'error': '"option" key is required'}), HTTP_400_BAD_REQUEST

    new_password = None
    option = payload['option']
    if password and option == 'resend':
        new_password = password
        password = None

    if not wallet.auth(password):
        return jsonify({'success': False, 'error': 'Incorrect password'}), HTTP_401_UNAUTHORIZED

    confirm = bool(int(request.args.get('confirm', 1)))
    params = payload.get('params', {})
    if option == 'resend':
        params['new_password'] = new_password

    result = spend_balance(wallet, option, confirm=confirm, **params)
    if isinstance(result, str):
        return jsonify({'success': False, 'error': result}), HTTP_500_INTERNAL_SERVER_ERROR

    result = {} if isinstance(result, bool) else result
    return jsonify({'success': True, **result})
