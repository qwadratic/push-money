from flask import Blueprint, jsonify

from pushmoney.controllers.core import generate_and_save_wallet, address_balance
from pushmoney.models import Wallet

bp_api = Blueprint('api', __name__, url_prefix='/api')


@bp_api.route('/')
def hello_world():
    return 'API ok.'


@bp_api.route('/generate', methods=['GET'])
def generate():
    wallet = generate_and_save_wallet()
    return jsonify({
        'address': wallet.address,
        'link_id': wallet.link_id
    })


@bp_api.route('/balance/<link_id>', methods=['GET'])
def balance(link_id):
    push = Wallet.get(link_id=link_id)
    if not push:
        return jsonify({'error': 'Link not exist'})

    response = address_balance(push.address)
    return jsonify(response)
