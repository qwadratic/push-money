from flask import Blueprint

bp_merchant = Blueprint('merchant', __name__)


bp_merchant.route('/')