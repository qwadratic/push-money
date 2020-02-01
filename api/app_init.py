from flask import Flask

from api.core import bp_api


def app_init():
    app = Flask(__name__)
    app.register_blueprint(bp_api)
    return app
