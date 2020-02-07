from flask import Flask

from api.core import bp_api
from api.root import bp_root
from api.sharing import bp_sharing
from helpers.misc import setup_logging

blueprints = [
    bp_api,
    bp_root,
    bp_sharing
]


def app_init():
    setup_logging()
    app = Flask(__name__)
    for bp in blueprints:
        app.register_blueprint(bp)
    return app
