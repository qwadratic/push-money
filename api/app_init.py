from flask import Flask

from api.core import bp_api
from api.root import bp_root


def app_init():
    app = Flask(__name__)
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_root)
    return app
