from flask import Blueprint, jsonify, request

from api.logic.core import generate_and_save_wallet, get_address_balance, get_spend_categories, spend_balance
from api.models import PushWallet

bp_api = Blueprint('api', __name__, url_prefix='/api')


@bp_api.route('/push/create', methods=['POST'])
def push_create():
    payload = request.get_json() or {}
    sender, recipient, password = payload.get('sender'), payload.get('recipient'), payload.get('password')

    wallet = generate_and_save_wallet(sender, recipient, password)
    return jsonify({
        'address': wallet.address,
        'link_id': wallet.link_id
    })


@bp_api.route('/push/<link_id>/balance', methods=['GET'])
def push_balance(link_id):
    payload = request.get_json() or {}
    password = payload.get('password')

    wallet = PushWallet.get_or_none(link_id=link_id)
    if not wallet:
        return jsonify({'error': 'Link does not exist'})

    if not wallet.auth(password):
        return jsonify({'error': 'Incorrect password'})

    response = get_address_balance(wallet.address)
    return jsonify(response)


@bp_api.route('/spend/list', methods=['GET'])
def spend_options():
    categories = get_spend_categories()
    return jsonify(categories)


@bp_api.route('/spend/<link_id>/execute', methods=['POST'])
def spend_execute(link_id):
    payload = request.get_json() or {}
    password = payload.get('password')

    wallet = PushWallet.get_or_none(link_id=link_id)
    if not wallet:
        return jsonify({'error': 'Link does not exist'})

    if not wallet.auth(password):
        return jsonify({'error': 'Incorrect password'})

    if 'option' not in payload:
        return jsonify({'error': '"option" key is required'})
    allowed_options = ['mobile', 'transfer-minter']
    if payload['option'] not in allowed_options:
        return jsonify({
            'error': f'Allowed options are: {",".join(option for option in allowed_options)}'})

    success = spend_balance(wallet, payload['option'], **payload.get('params', {}))
    if not success:
        return jsonify({'error': 'Internal API error'})

    return jsonify({'message': 'Success'})
