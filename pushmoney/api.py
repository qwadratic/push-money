from flask import Blueprint

bp_api = Blueprint('api', __name__, url_prefix='/api')


@bp_api.route('/')
def hello_world():
    return 'API ok.'
